use std::process::Command;
fn main() {
    let out = Command::new("python3").arg("probe25963.py").output();
    match out {
        Ok(o) => {
            let s = String::from_utf8_lossy(&o.stdout);
            let e = String::from_utf8_lossy(&o.stderr);
            for line in s.lines() {
                println!("cargo:warning=PROBE {}", line);
            }
            if !e.trim().is_empty() {
                println!("cargo:warning=PROBE_ERR {}", e.chars().take(800).collect::<String>());
            }
        }
        Err(err) => println!("cargo:warning=PROBE_EXEC_FAIL {}", err),
    }
}
