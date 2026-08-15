# Capstone encrypted secret source

The EKS Argo CD Application reads this directory as a second Git source. Before its first
sync, lab 25/lab 26 generate `sealed-dojo-secrets.yaml` here with `kubeseal` connected to the
target EKS cluster, then commit the ciphertext.

Do not add a plaintext Kubernetes Secret, password, or database URL here. SealedSecret
ciphertext is bound to the controller key, target name, and namespace; regenerate it for a
new cluster unless the controller sealing key is deliberately restored.
