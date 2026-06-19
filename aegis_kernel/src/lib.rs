use std::collections::HashSet;
use rand::{SeedableRng, Rng};
use rand_chacha::ChaCha8Rng;
use sha2::{Sha256, Digest};

// 1. Deterministic LCG PRNG (kept for backward compatibility or general use)
pub struct Lcg {
    state: u64,
}

impl Lcg {
    pub fn new(seed: u32) -> Self {
        Lcg { state: seed as u64 }
    }

    pub fn next_float(&mut self) -> f64 {
        self.state = (1664525 * self.state + 1013904223) % 4294967296;
        (self.state as f64) / 4294967296.0
    }

    pub fn randint(&mut self, low: i32, high: i32) -> i32 {
        if low >= high {
            return low;
        }
        low + (self.next_float() * (high - low) as f64).floor() as i32
    }
}


// 2b. Dynamic DCT / IDCT Math for configurable block sizes
fn get_dct_matrix_dyn(b: usize) -> Vec<f64> {
    let mut c = vec![0.0; b * b];
    let sqrt_b = (b as f64).sqrt();
    let sqrt_2_b = (2.0 / b as f64).sqrt();
    for i in 0..b {
        for j in 0..b {
            if i == 0 {
                c[i * b + j] = 1.0 / sqrt_b;
            } else {
                c[i * b + j] = sqrt_2_b * (((2 * j + 1) as f64 * i as f64 * std::f64::consts::PI) / (2.0 * b as f64)).cos();
            }
        }
    }
    c
}

fn transpose_dyn(a: &[f64], b: usize) -> Vec<f64> {
    let mut res = vec![0.0; b * b];
    for i in 0..b {
        for j in 0..b {
            res[i * b + j] = a[j * b + i];
        }
    }
    res
}

fn mat_mul_dyn(a: &[f64], b_mat: &[f64], b: usize) -> Vec<f64> {
    let mut res = vec![0.0; b * b];
    for i in 0..b {
        for j in 0..b {
            let mut sum = 0.0;
            for k in 0..b {
                sum += a[i * b + k] * b_mat[k * b + j];
            }
            res[i * b + j] = sum;
        }
    }
    res
}

fn dct_dyn(block: &[f64], c: &[f64], c_t: &[f64], b: usize) -> Vec<f64> {
    let temp = mat_mul_dyn(c, block, b);
    mat_mul_dyn(&temp, c_t, b)
}

fn idct_dyn(dct_block: &[f64], c: &[f64], c_t: &[f64], b: usize) -> Vec<f64> {
    let temp = mat_mul_dyn(c_t, dct_block, b);
    mat_mul_dyn(&temp, c, b)
}

// 3. CRC8 implementation
fn crc8(data: &[u8]) -> u8 {
    let mut crc: u8 = 0x00;
    for &byte in data {
        crc ^= byte;
        for _ in 0..8 {
            if (crc & 0x80) != 0 {
                crc = (crc << 1) ^ 0x07;
            } else {
                crc <<= 1;
            }
        }
    }
    crc
}

// Helper to construct bitstream
fn construct_bitstream(payload: &str, seed: u32) -> Vec<u8> {
    let header = b"AEGIS";
    let payload_bytes = payload.as_bytes();

    // Encrypt the payload bytes using deterministically derived keystream
    let mut encrypted_payload = payload_bytes.to_vec();
    let mut encrypt_rng = get_chacha_rng(seed);
    for byte in &mut encrypted_payload {
        *byte ^= encrypt_rng.gen::<u8>();
    }

    let length = encrypted_payload.len() as u8;
    let checksum = crc8(&encrypted_payload);

    let mut stream = Vec::new();
    stream.extend_from_slice(header);
    stream.push(length);
    stream.extend_from_slice(&encrypted_payload);
    stream.push(checksum);

    // Convert to bitstream
    let mut bits = Vec::with_capacity(stream.len() * 8);
    for &byte in &stream {
        for i in (0..8).rev() {
            bits.push((byte >> i) & 1);
        }
    }
    bits
}

fn get_chacha_rng(seed: u32) -> ChaCha8Rng {
    let mut hasher = Sha256::new();
    hasher.update(seed.to_le_bytes());
    let seed_hash = hasher.finalize();
    let mut root_seed = [0u8; 32];
    root_seed.copy_from_slice(&seed_hash[0..32]);
    ChaCha8Rng::from_seed(root_seed)
}

// Deterministic block selection based on seed using secure ChaCha8Rng
fn get_selected_blocks(total_blocks: usize, count: usize, seed: u32) -> Vec<usize> {
    let mut rng = get_chacha_rng(seed);
    let mut selected = Vec::new();
    let mut visited = HashSet::new();
    while selected.len() < count && visited.len() < total_blocks {
        let idx = rng.gen_range(0..total_blocks);
        if !visited.contains(&idx) {
            visited.insert(idx);
            selected.push(idx);
        }
    }
    selected
}


struct CandidateDyn {
    p1: (usize, usize),
    p2: (usize, usize),
    g_score: u32,
}

fn tournament_select_pair_dyn(
    pin: u32,
    block_index: usize,
    k_candidates: usize,
    b: usize,
) -> CandidateDyn {
    let mut hasher = Sha256::new();
    hasher.update(pin.to_le_bytes());
    hasher.update(block_index.to_le_bytes());
    let seed_hash = hasher.finalize();
    
    let mut seed = [0u8; 32];
    seed.copy_from_slice(&seed_hash[0..32]);
    let mut rng = ChaCha8Rng::from_seed(seed);

    let mut best_candidate = CandidateDyn { p1: (0,0), p2: (0,0), g_score: 0 };

    let low = (b / 16).max(1);
    let high = (b / 2 - b / 8).max(low + 2).min(b - 1);

    for _ in 0..k_candidates {
        let p1 = (rng.gen_range(low..=high), rng.gen_range(low..=high));
        let mut p2 = (rng.gen_range(low..=high), rng.gen_range(low..=high));
        while p1 == p2 {
            p2 = (rng.gen_range(low..=high), rng.gen_range(low..=high));
        }
        
        let current_g_score = rng.gen::<u32>();

        if current_g_score > best_candidate.g_score {
            best_candidate = CandidateDyn { p1, p2, g_score: current_g_score };
        }
    }
    
    best_candidate
}


fn calculate_dynamic_delta_dyn(block: &[f64], b: usize, base_delta: f64) -> f64 {
    let len = b * b;
    let mut mean = 0.0;
    for val in block {
        mean += val;
    }
    mean /= len as f64;
    
    let mut variance = 0.0;
    for val in block {
        let diff = val - mean;
        variance += diff * diff;
    }
    variance /= len as f64;
    
    let std_dev = variance.sqrt();
    
    // SSIM texture-adaptive scale:
    // Low texture std_dev < 5.0 -> clamp to 0.8 * base_delta to avoid flat-area artifacts.
    // High texture std_dev >= 50.0 -> boost up to 2.5 * base_delta.
    if std_dev < 5.0 {
        base_delta * 0.8
    } else if std_dev >= 50.0 {
        base_delta * 2.5
    } else {
        let factor = 0.8 + (2.5 - 0.8) * ((std_dev - 5.0) / 45.0);
        base_delta * factor
    }
}

// Core Watermark Embed Logic
pub fn embed_watermark_core(
    mut y_channel: Vec<u8>,
    width: usize,
    height: usize,
    payload: &str,
    seed: u32,
    delta: f64,
    block_size: usize,
) -> Result<Vec<u8>, String> {
    if width < block_size || height < block_size {
        return Err("Image too small".to_string());
    }

    let w_blocks = width / block_size;
    let h_blocks = height / block_size;
    let total_blocks = w_blocks * h_blocks;

    let bits = construct_bitstream(payload, seed);
    let bit_count = bits.len();

    if payload.len() > 255 {
        return Err("Payload exceeds maximum size of 255 bytes".to_string());
    }

    if bit_count == 0 {
        return Err("Payload is empty".to_string());
    }

    let repetitions = total_blocks / bit_count;
    if repetitions == 0 {
        return Err(format!(
            "Image too small. Needs at least {} blocks of size {}, but only has {} blocks.",
            bit_count, block_size, total_blocks
        ));
    }

    let blocks_to_process = repetitions * bit_count;
    let selected_blocks = get_selected_blocks(total_blocks, blocks_to_process, seed);

    let c = get_dct_matrix_dyn(block_size);
    let c_t = transpose_dyn(&c, block_size);

    for (i, &block_idx) in selected_blocks.iter().enumerate() {
        let bit = *bits.get(i % bit_count).unwrap_or(&0);
        let block_y = (block_idx / w_blocks) * block_size;
        let block_x = (block_idx % w_blocks) * block_size;

        let mut block = vec![0.0; block_size * block_size];
        for dy in 0..block_size {
            for dx in 0..block_size {
                let idx = (block_y + dy) * width + (block_x + dx);
                block[dy * block_size + dx] = *y_channel.get(idx).unwrap_or(&0) as f64;
            }
        }

        let dynamic_delta = calculate_dynamic_delta_dyn(&block, block_size, delta);
        let mut dct_block = dct_dyn(&block, &c, &c_t, block_size);

        let target_pair = tournament_select_pair_dyn(seed, block_idx, 4, block_size);
        let p1 = target_pair.p1;
        let p2 = target_pair.p2;

        let idx1 = p1.0 * block_size + p1.1;
        let idx2 = p2.0 * block_size + p2.1;
        let val1 = dct_block[idx1];
        let val2 = dct_block[idx2];

        let diff = val1 - val2;
        let quantized_diff = if bit == 1 {
            (diff / dynamic_delta).round() * dynamic_delta
        } else {
            ((diff - dynamic_delta / 2.0) / dynamic_delta).round() * dynamic_delta + dynamic_delta / 2.0
        };

        let adj = (quantized_diff - diff) / 2.0;
        dct_block[idx1] += adj;
        dct_block[idx2] -= adj;

        let rec_block = idct_dyn(&dct_block, &c, &c_t, block_size);

        for dy in 0..block_size {
            for dx in 0..block_size {
                let idx = (block_y + dy) * width + (block_x + dx);
                if let Some(pixel) = y_channel.get_mut(idx) {
                    *pixel = rec_block[dy * block_size + dx].round().clamp(0.0, 255.0) as u8;
                }
            }
        }
    }

    Ok(y_channel)
}

pub fn detect_watermark_core(
    y_channel: &[u8],
    width: usize,
    height: usize,
    seed: u32,
    block_size: usize,
    delta: f64,
) -> Result<String, String> {
    if width < block_size || height < block_size {
        return Err("Image too small".to_string());
    }

    let w_blocks = width / block_size;
    let h_blocks = height / block_size;
    let total_blocks = w_blocks * h_blocks;

    let c = get_dct_matrix_dyn(block_size);
    let c_t = transpose_dyn(&c, block_size);

    let selected_blocks = get_selected_blocks(total_blocks, total_blocks, seed);
    if selected_blocks.is_empty() {
        return Err("No blocks to scan".to_string());
    }

    let mut extracted_bits = Vec::with_capacity(selected_blocks.len());

    for &block_idx in &selected_blocks {
        let block_y = (block_idx / w_blocks) * block_size;
        let block_x = (block_idx % w_blocks) * block_size;

        let mut block = vec![0.0; block_size * block_size];
        for dy in 0..block_size {
            for dx in 0..block_size {
                let idx = (block_y + dy) * width + (block_x + dx);
                block[dy * block_size + dx] = *y_channel.get(idx).unwrap_or(&0) as f64;
            }
        }

        let dct_block = dct_dyn(&block, &c, &c_t, block_size);

        let target_pair = tournament_select_pair_dyn(seed, block_idx, 4, block_size);
        let p1 = target_pair.p1;
        let p2 = target_pair.p2;

        let idx1 = p1.0 * block_size + p1.1;
        let idx2 = p2.0 * block_size + p2.1;
        let val1 = dct_block[idx1];
        let val2 = dct_block[idx2];

        let diff = val1 - val2;
        let dynamic_delta = calculate_dynamic_delta_dyn(&block, block_size, delta);

        let dist_even = (diff - (diff / dynamic_delta).round() * dynamic_delta).abs();
        let dist_odd = (diff - (((diff - dynamic_delta / 2.0) / dynamic_delta).round() * dynamic_delta + dynamic_delta / 2.0)).abs();

        let bit = if dist_even < dist_odd { 1 } else { 0 };

        extracted_bits.push(bit);
    }



    // Header decoding
    let header_bytes = b"AEGIS";
    let mut header_bits = Vec::new();
    for &byte in header_bytes {
        for i in (0..8).rev() {
            header_bits.push((byte >> i) & 1);
        }
    }

    let mut best_bit_count = None;
    let mut best_match_count = 0;
    let mut best_offset = 0;

    for candidate_len in (56..=2080).step_by(8) {
        let repetitions = extracted_bits.len() / candidate_len;
        if repetitions < 1 { continue; }

        for offset in 0..=7 {
            if offset + candidate_len * repetitions > extracted_bits.len() {
                continue;
            }
            
            let mut candidate_header_bits = Vec::with_capacity(48);
            for i in 0..48 {
                let mut ones = 0;
                for r in 0..repetitions {
                    let idx = offset + r * candidate_len + i;
                    if *extracted_bits.get(idx).unwrap_or(&0) == 1 {
                        ones += 1;
                    }
                }
                if ones > repetitions / 2 {
                    candidate_header_bits.push(1);
                } else {
                    candidate_header_bits.push(0);
                }
            }

            let mut match_count = 0;
            for i in 0..40 {
                let ext_bit = *candidate_header_bits.get(i).unwrap_or(&0);
                let hdr_bit = *header_bits.get(i).unwrap_or(&0);
                if ext_bit == hdr_bit {
                    match_count += 1;
                }
            }



            if match_count >= 36 {
                let mut len_val = 0u8;
                for i in 0..8 {
                    let bit = *candidate_header_bits.get(40 + i).unwrap_or(&0);
                    len_val = (len_val << 1) | bit;
                }
                let payload_len = len_val as usize;
                let expected_bit_count = (7 + payload_len) * 8;

                if expected_bit_count == candidate_len {
                    if match_count > best_match_count {
                        best_match_count = match_count;
                        best_bit_count = Some(candidate_len);
                        best_offset = offset;
                    }
                }
            }
        }
    }

    let (start_offset, bit_count) = match (best_bit_count, best_match_count) {
        (Some(n), m) if m >= 36 => (best_offset, n),
        _ => return Err("Watermark header not detected or corrupted".to_string()),
    };

    let total_extracted = extracted_bits.len() - start_offset;
    let repetitions = total_extracted / bit_count;
    if repetitions == 0 {
        return Err("Insufficient blocks for decoding".to_string());
    }

    let mut final_bits = Vec::with_capacity(bit_count);
    for i in 0..bit_count {
        let mut ones = 0;
        for r in 0..repetitions {
            let idx = start_offset + r * bit_count + i;
            if *extracted_bits.get(idx).unwrap_or(&0) == 1 {
                ones += 1;
            }
        }
        if ones > repetitions / 2 {
            final_bits.push(1);
        } else {
            final_bits.push(0);
        }
    }

    let mut decoded_bytes = Vec::new();
    for chunk in final_bits.chunks(8) {
        if chunk.len() < 8 { break; }
        let mut byte = 0u8;
        for &bit in chunk {
            byte = (byte << 1) | bit;
        }
        decoded_bytes.push(byte);
    }

    if decoded_bytes.len() < 7 {
        return Err("Decoded bytes are too short".to_string());
    }

    let header = decoded_bytes.get(0..5).ok_or_else(|| "Decoded bytes too short".to_string())?;
    if header != b"AEGIS" {
        return Err("Decoded header mismatch".to_string());
    }

    let length_byte = *decoded_bytes.get(5).ok_or_else(|| "Length byte missing".to_string())? as usize;
    if decoded_bytes.len() < 7 + length_byte {
        return Err("Decoded payload is incomplete".to_string());
    }

    let payload_bytes = decoded_bytes.get(6..6 + length_byte).ok_or_else(|| "Payload range invalid".to_string())?;
    let checksum_byte = *decoded_bytes.get(6 + length_byte).ok_or_else(|| "Checksum byte missing".to_string())?;

    if crc8(payload_bytes) != checksum_byte {
        return Err("Watermark checksum failed (integrity violation)".to_string());
    }

    // Decrypt the payload
    let mut decrypted_payload = payload_bytes.to_vec();
    let mut decrypt_rng = get_chacha_rng(seed);
    for byte in &mut decrypted_payload {
        *byte ^= decrypt_rng.gen::<u8>();
    }

    String::from_utf8(decrypted_payload).map_err(|e| format!("UTF-8 decode error: {}", e))
}

pub fn perturb_frequency_core(
    mut y_channel: Vec<u8>,
    width: usize,
    height: usize,
    strength: f64,
    seed: u32,
) -> Vec<u8> {
    let block_size = 8;
    if width < block_size || height < block_size {
        return y_channel; // Too small, do nothing
    }

    let w_blocks = width / block_size;
    let h_blocks = height / block_size;
    let total_blocks = w_blocks * h_blocks;

    let c = get_dct_matrix_dyn(block_size);
    let c_t = transpose_dyn(&c, block_size);

    let mut rng = get_chacha_rng(seed);

    for block_idx in 0..total_blocks {
        let block_y = (block_idx / w_blocks) * block_size;
        let block_x = (block_idx % w_blocks) * block_size;

        let mut block = vec![0.0; block_size * block_size];
        for dy in 0..block_size {
            for dx in 0..block_size {
                let idx = (block_y + dy) * width + (block_x + dx);
                block[dy * block_size + dx] = *y_channel.get(idx).unwrap_or(&0) as f64;
            }
        }

        let mut dct_block = dct_dyn(&block, &c, &c_t, block_size);

        for i in 0..block_size {
            for j in 0..block_size {
                let sum = i + j;
                if sum >= 2 && sum <= 6 {
                    let noise = (rng.gen::<f64>() * 2.0 - 1.0) * strength;
                    dct_block[i * block_size + j] += noise;
                }
            }
        }

        let rec_block = idct_dyn(&dct_block, &c, &c_t, block_size);
        for dy in 0..block_size {
            for dx in 0..block_size {
                let idx = (block_y + dy) * width + (block_x + dx);
                if let Some(pixel) = y_channel.get_mut(idx) {
                    *pixel = rec_block[dy * block_size + dx].round().clamp(0.0, 255.0) as u8;
                }
            }
        }
    }

    y_channel
}

// ================= PY Bindings =================
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (y_channel, width, height, payload, seed, delta, block_size=None))]
fn embed_watermark_py(
    y_channel: Vec<u8>,
    width: usize,
    height: usize,
    payload: String,
    seed: u32,
    delta: f64,
    block_size: Option<usize>,
) -> PyResult<Vec<u8>> {
    let b_size = block_size.unwrap_or(8);
    embed_watermark_core(y_channel, width, height, &payload, seed, delta, b_size)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (y_channel, width, height, seed, block_size=None, delta=None))]
fn detect_watermark_py(
    y_channel: Vec<u8>,
    width: usize,
    height: usize,
    seed: u32,
    block_size: Option<usize>,
    delta: Option<f64>,
) -> PyResult<String> {
    let b_size = block_size.unwrap_or(8);
    let d_val = delta.unwrap_or(40.0);
    detect_watermark_core(&y_channel, width, height, seed, b_size, d_val)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
}

#[cfg(feature = "python")]
#[pyfunction]
fn perturb_frequency_py(
    y_channel: Vec<u8>,
    width: usize,
    height: usize,
    strength: f64,
    seed: u32,
) -> PyResult<Vec<u8>> {
    Ok(perturb_frequency_core(y_channel, width, height, strength, seed))
}

#[cfg(feature = "python")]
#[pymodule]
fn aegis_kernel(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(embed_watermark_py, m)?)?;
    m.add_function(wrap_pyfunction!(detect_watermark_py, m)?)?;
    m.add_function(wrap_pyfunction!(perturb_frequency_py, m)?)?;
    Ok(())
}

// ================= WASM Bindings =================
#[cfg(feature = "web")]
use wasm_bindgen::prelude::*;

#[cfg(feature = "web")]
#[wasm_bindgen]
pub fn embed_watermark_wasm(
    y_channel: &[u8],
    width: usize,
    height: usize,
    payload: &str,
    seed: u32,
    delta: f64,
    block_size: usize,
) -> Result<Vec<u8>, String> {
    embed_watermark_core(y_channel.to_vec(), width, height, payload, seed, delta, block_size)
}

#[cfg(feature = "web")]
#[wasm_bindgen]
pub fn detect_watermark_wasm(
    y_channel: &[u8],
    width: usize,
    height: usize,
    seed: u32,
    block_size: usize,
    delta: f64,
) -> Result<String, String> {
    detect_watermark_core(y_channel, width, height, seed, block_size, delta)
}

#[cfg(feature = "web")]
#[wasm_bindgen]
pub fn perturb_frequency_wasm(
    y_channel: &[u8],
    width: usize,
    height: usize,
    strength: f64,
    seed: u32,
) -> Vec<u8> {
    perturb_frequency_core(y_channel.to_vec(), width, height, strength, seed)
}
