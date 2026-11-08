# Security policy

The Ed25519 private signing key is the root of trust for Premium entitlements.

- Generate it only on a trusted administrator machine.
- Keep it outside this repository, preferably encrypted at rest and backed up securely.
- Never put it in the Android APK, GitHub source, Actions secrets unless a future audited signing pipeline specifically requires it, logs or releases.
- Distribute only the public key to the Android application.
- Restrict generator access to authorised administrators.
- Plan public-key rotation before production issuance.

Activation codes are bearer secrets. Deliver them privately and never put them in commits, issues, screenshots or support logs.

## Important limitations

This first version is a local offline generator and verifier. It does not process payments, provide customer authentication, run a redemption API, enforce single-use redemption, bind a licence to devices or revoke licences remotely. The generated signed document is not proof of payment on its own. Those service-side controls and Android verification must be implemented before real customers are activated.
