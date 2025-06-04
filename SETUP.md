### Solvers
## Astrometry.net
Installed to system, requires index files.

## Tetra3
Installed via Python package manager (PIP). includes required files. 

## Cedar
An improvement/extension to Tetra3. 

Requires Rust/cargo (https://www.rust-lang.org/tools/install)

Uses new centroiding and solving functionality. 

Clone https://github.com/smroid/cedar-solve to home
Update PYTHONPATH:
`export PYTHONPATH=/home/pi/projects/cedar-solve/tetra3`

Clone https://github.com/smroid/cedar-detect to home
Enter `/cedar-detect` and build `cargo build --release`

Copy executable into cedar-solve
`cp /home/pi/cedar-detect/target/release/cedar-detect-server /home/pi/cedar-solve/tetra3/bin`


