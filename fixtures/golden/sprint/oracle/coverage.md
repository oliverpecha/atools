# coverage.md - requirement -> proofs, mutant -> proofs expected to kill it
R1 -> 01_public.sh, probe.sh
R2 -> 02_no_email.sh
R3 -> 03_private_404.sh
mutants/contact_leak.patch -> 02_no_email.sh
mutants/private_200.patch -> 03_private_404.sh
mutants/photo_count_off.patch -> probe.sh
mutants/avatar_drop.patch -> 01_public.sh
