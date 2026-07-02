{{/*
dojo-lib.service — a ClusterIP Service selecting app=<name>.
Call with: include "dojo-lib.service" (dict "name" "api" "port" 8080)
targetPort defaults to port.
*/}}
{{- define "dojo-lib.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ .name }}
spec:
  selector:
    app: {{ .name }}
  ports:
    - port: {{ .port }}
      targetPort: {{ .targetPort | default .port }}
{{- end -}}
