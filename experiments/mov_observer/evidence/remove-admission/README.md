# Admission escape removed; restricted installer certificate withdrawn

This checkpoint revokes the claimed installer completion in a2126801. That
commit's theorem assumed requested memory already matched ambient memory. It
proved a restricted loader fact, not the user's requested installer. Earlier
positive review of that restriction did not satisfy the user's telos.

Profile.admitted and its antecedents are removed from ComponentObligations,
BootstrapObligation, InstallationCoverage and InstallerContract. Installation
now quantifies over every wanted/ambient state in the fixed represented model.
No replacement exclusion predicate is introduced.

The derived restrictive movInstallerProfile, its coverage proof, and the
mov_installer_contract theorem are removed. Valid loader-access lemmas remain;
none is a replacement claim of completed installation. The historical evidence
in evidence/mov-installer describes the revoked restricted theorem only.

This is revocation of an acceptance escape, NOT completion of a real memory
installer. The existing MOV boundary memory equality and outside-slot frame
still preserve ambient memory; actual requested memory writes need different
boundary/frame definitions and implementation. Broader independent audits are
ongoing and are not represented as satisfied by this checkpoint.

Original Astra Max reviewed the immediate removal and acknowledged the earlier
purpose failure: it had accepted a documented/satisfiable restricted theorem
as completion despite the user's request. Two fresh Astra Max reviewers are
independently auditing the standard, implementation and review failure.

Base a2126801b431358d4cce746bb80b02518b6b0b62.
Bootstrap.lean SHA256 ecb38c650f550d8b6cec10ca12b5cfb5c15c6a97f3032fdb92400de081b36827.
MovInstaller.lean SHA256 9b3a44db695a116e5099bc907399efca5ce7daa94886066a0e62c1e661c74205.
Validation: NixOS Lean4.34.0, AYXG324752afe80b05d7fd8854834725cf5ee360f173.
Unit observer-no-admission-2.service, invocation be9ac11444fa4470ab1efb628bae0ae9,
fleet-build.slice, user heartpunk, 2GiB/no swap/one CPU, TasksMax64.
See final typecheck.log and resources.txt for outcome. No native test is claimed.
