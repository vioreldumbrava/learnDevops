{{/*
dojo-lib.deployment — the one Deployment shape every stateless Dojo workload uses.
Required keys: name, replicas, image, pullPolicy.
Optional keys: command (list), port (int), envFromConfigMap (name), env (list of
env entries, verbatim), livenessProbe / readinessProbe (probe spec, verbatim),
resources (requests/limits map).
Optional blocks render only when the caller passes them — that keeps one define
serving api (probes+env), frontend (probe only) and worker (command, no port).
*/}}
{{- define "dojo-lib.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .name }}
spec:
  replicas: {{ .replicas }}
  selector:
    matchLabels:
      app: {{ .name }}
  template:
    metadata:
      labels:
        app: {{ .name }}
    spec:
      containers:
        - name: {{ .name }}
          image: {{ .image | quote }}
          imagePullPolicy: {{ .pullPolicy }}
          {{- with .command }}
          command:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .port }}
          ports:
            - containerPort: {{ . }}
          {{- end }}
          {{- with .envFromConfigMap }}
          envFrom:
            - configMapRef:
                name: {{ . }}
          {{- end }}
          {{- with .env }}
          env:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .livenessProbe }}
          livenessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .readinessProbe }}
          readinessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .resources }}
          resources:
            {{- toYaml . | nindent 12 }}
          {{- end }}
{{- end -}}
