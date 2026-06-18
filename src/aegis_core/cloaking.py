import os
import torch
import torchvision.models as models
from PIL import Image
from torchvision import transforms

class PgdCloaker:
    def __init__(self, surrogate_name: str = "mobilenet_v2", offline: bool = False):
        """
        Initializes the PGD Cloaker with the chosen surrogate model.
        
        Args:
            surrogate_name: Name of the torchvision model (resnet18, mobilenet_v2, mobilenet_v3_large)
            offline: If True, restricts PyTorch from making download requests (uses local cache only).
        """
        if os.environ.get("AEGIS_NO_CLIP") == "1" or os.environ.get("AEGIS_NO_FORENSICS") == "1":
            print("[INFO] PgdCloaker initialization bypassed via environment variable.")
            self.model = None
            self.device = "cpu"
            return

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[INFO] PgdCloaker initializing on device: {self.device}")
        
        if offline:
            # Set environment variables to prevent torchvision from downloading weights
            os.environ["TORCH_HUB_OFFLINE"] = "1"
            print("[INFO] Offline mode enabled. Forcing local cache for model weights.")

        self.surrogate_name = surrogate_name.lower()
        self.model = self._load_model()
        self.model.to(self.device)
        self.model.eval()
        
        # Freeze all model parameters
        for param in self.model.parameters():
            param.requires_grad = False

    def _load_model(self):
        """Loads the torchvision surrogate model weights."""
        try:
            if self.surrogate_name == "resnet18":
                weights = models.ResNet18_Weights.DEFAULT
                return models.resnet18(weights=weights)
            elif self.surrogate_name == "mobilenet_v3_large":
                weights = models.MobileNet_V3_Large_Weights.DEFAULT
                return models.mobilenet_v3_large(weights=weights)
            else:
                # Default/Fallback is MobileNet V2
                if self.surrogate_name != "mobilenet_v2":
                    print(f"[WARN] Unknown surrogate '{self.surrogate_name}'. Falling back to mobilenet_v2.")
                weights = models.MobileNet_V2_Weights.DEFAULT
                return models.mobilenet_v2(weights=weights)
        except OSError as e:
            if "offline" in str(e).lower() or os.environ.get("TORCH_HUB_OFFLINE") == "1":
                raise RuntimeError(
                    f"Model weights for '{self.surrogate_name}' are not cached locally. "
                    "Please run without the --offline flag to download weights first."
                ) from e
            raise e

    def cloak_image(self, image_path: str, eps: float = 8.0, steps: int = 40) -> Image.Image:
        """
        Applies Projected Gradient Descent (PGD) to the image to disrupt AI classification.
        
        Args:
            image_path: Path to the original image.
            eps: Epsilon budget in 0-255 scale (L-infinity constraint).
            steps: Number of gradient ascent iterations.
            
        Returns:
            A PIL Image containing the perturbed/cloaked image.
        """
        # 1. Load and prepare the original image
        orig_img = Image.open(image_path).convert("RGB")
        if self.model is None:
            return orig_img
        w, h = orig_img.size
        
        # Transform to normalized tensor for optimizer, but do it dynamically
        to_tensor = transforms.ToTensor()
        x = to_tensor(orig_img).unsqueeze(0).to(self.device) # Shape: [1, 3, H, W], Range: [0, 1]
        
        # 2. Setup parameters
        epsilon_val = eps / 255.0
        alpha_val = epsilon_val / 10.0 if steps > 0 else 0.0
        
        # Initialize perturbation delta in the range [-eps, eps]
        delta = torch.zeros_like(x, requires_grad=True)
        
        # Standard ImageNet normalization parameters (needed for the model forward pass)
        mean = torch.tensor([0.485, 0.456, 0.406], device=self.device).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=self.device).view(1, 3, 1, 1)
        
        # Get the original class prediction (the target we want to move away from)
        with torch.no_grad():
            x_clean_resized = torch.nn.functional.interpolate(x, size=(224, 224), mode="bilinear", align_corners=False)
            x_clean_normalized = (x_clean_resized - mean) / std
            clean_logits = self.model(x_clean_normalized)
            pred_label = clean_logits.argmax(dim=1)
            
        print(f"[INFO] Clean prediction class ID: {pred_label.item()}")
        print(f"[INFO] Optimizing adversarial cloak (eps={eps}, steps={steps})...")
        
        # 3. PGD Optimization Loop
        for step in range(steps):
            x_adv = x + delta
            x_adv = torch.clamp(x_adv, 0.0, 1.0)
            
            # Interpolate to 224x224 (differentiable operation)
            x_resized = torch.nn.functional.interpolate(x_adv, size=(224, 224), mode="bilinear", align_corners=False)
            x_normalized = (x_resized - mean) / std
            
            # Forward pass
            logits = self.model(x_normalized)
            
            # Untargeted Cross Entropy Loss (we want to maximize this loss)
            loss = torch.nn.functional.cross_entropy(logits, pred_label)
            
            # Backward pass to obtain gradients w.r.t delta
            loss.backward()
            
            # Gradient ascent step: delta = delta + alpha * sign(grad)
            with torch.no_grad():
                grad_sign = delta.grad.sign()
                delta += alpha_val * grad_sign
                # Project back to L-infinity epsilon ball
                delta.clamp_(-epsilon_val, epsilon_val)
                
            delta.grad.zero_()
            
            if (step + 1) % 10 == 0 or step == 0:
                print(f"  PGD Step {step + 1}/{steps} | Loss: {loss.item():.4f}")
                
        # 4. Reconstruct and return final image
        with torch.no_grad():
            x_final = torch.clamp(x + delta, 0.0, 1.0).squeeze(0).cpu()
            
        # Convert tensor back to PIL Image
        to_pil = transforms.ToPILImage()
        perturbed_img = to_pil(x_final)
        
        # Preserve original image format metadata / size
        return perturbed_img
