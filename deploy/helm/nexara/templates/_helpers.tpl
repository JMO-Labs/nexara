{{- define "nexara.fullname" -}}{{ .Release.Name }}-{{ .Chart.Name }}{{- end }}
{{- define "nexara.image" -}}{{ .Values.image.registry }}/{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}{{- end }}
{{- define "nexara.labels" -}}
app.kubernetes.io/name: nexara
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}
{{- define "nexara.selector" -}}
app.kubernetes.io/name: nexara
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}
{{- define "nexara.appSecret" -}}{{ .Values.secrets.existingSecret | default (printf "%s-app" (include "nexara.fullname" .)) }}{{- end }}
{{- define "nexara.dbSecret" -}}
{{- if .Values.postgresql.enabled }}{{ include "nexara.fullname" . }}-db
{{- else if .Values.postgresql.external.existingSecret }}{{ .Values.postgresql.external.existingSecret }}
{{- else }}{{ include "nexara.fullname" . }}-db{{- end }}
{{- end }}
{{- define "nexara.s3Secret" -}}{{ .Values.storage.s3.existingSecret | default (printf "%s-s3" (include "nexara.fullname" .)) }}{{- end }}
{{- define "nexara.dbHost" -}}{{ if .Values.postgresql.enabled }}{{ include "nexara.fullname" . }}-postgresql{{ else }}{{ required "postgresql.external.host is required when postgresql.enabled=false" .Values.postgresql.external.host }}{{ end }}{{- end }}
{{- define "nexara.redisUrl" -}}{{ if .Values.valkey.enabled }}redis://{{ include "nexara.fullname" . }}-valkey:6379{{ else }}{{ required "valkey.external.url is required when valkey.enabled=false" .Values.valkey.external.url }}{{ end }}{{- end }}

{{/* Shared container env for api/worker/beat. Pass root context. */}}
{{- define "nexara.env" -}}
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "nexara.dbSecret" . }}
      key: database-password
- name: DATABASE_URL
  value: "postgresql+asyncpg://{{ if .Values.postgresql.enabled }}{{ .Values.postgresql.username }}{{ else }}{{ .Values.postgresql.external.username }}{{ end }}:$(DB_PASSWORD)@{{ include "nexara.dbHost" . }}:{{ if .Values.postgresql.enabled }}5432{{ else }}{{ .Values.postgresql.external.port }}{{ end }}/{{ if .Values.postgresql.enabled }}{{ .Values.postgresql.database }}{{ else }}{{ .Values.postgresql.external.database }}{{ end }}"
- name: REDIS_URL
  value: {{ include "nexara.redisUrl" . | quote }}
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "nexara.appSecret" . }}
      key: secret-key
{{- if eq .Values.storage.backend "s3" }}
- name: S3_ACCESS_KEY
  valueFrom:
    secretKeyRef: {name: {{ include "nexara.s3Secret" . }}, key: s3-access-key}
- name: S3_SECRET_KEY
  valueFrom:
    secretKeyRef: {name: {{ include "nexara.s3Secret" . }}, key: s3-secret-key}
{{- end }}
envFrom:
  - configMapRef:
      name: {{ include "nexara.fullname" . }}
{{- end }}
