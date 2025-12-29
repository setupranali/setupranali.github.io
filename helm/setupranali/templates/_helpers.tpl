{{/*
Expand the name of the chart.
*/}}
{{- define "setupranali.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "setupranali.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "setupranali.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "setupranali.labels" -}}
helm.sh/chart: {{ include "setupranali.chart" . }}
{{ include "setupranali.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "setupranali.selectorLabels" -}}
app.kubernetes.io/name: {{ include "setupranali.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "setupranali.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "setupranali.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use
*/}}
{{- define "setupranali.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- include "setupranali.fullname" . }}
{{- end }}
{{- end }}

{{/*
Get the encryption key secret key name
*/}}
{{- define "setupranali.encryptionKeySecretKey" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecretKeys.encryptionKey }}
{{- else }}
UBI_SECRET_KEY
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "setupranali.redisHost" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "setupranali.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Redis port
*/}}
{{- define "setupranali.redisPort" -}}
{{- if .Values.redis.enabled }}
6379
{{- else }}
{{- .Values.externalRedis.port | default 6379 }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "setupranali.redisUrl" -}}
{{- $host := include "setupranali.redisHost" . }}
{{- $port := include "setupranali.redisPort" . }}
{{- printf "redis://%s:%s" $host $port }}
{{- end }}

{{/*
Create the name of the catalog configmap
*/}}
{{- define "setupranali.catalogConfigMapName" -}}
{{- if .Values.catalog.existingConfigMap }}
{{- .Values.catalog.existingConfigMap }}
{{- else }}
{{- printf "%s-catalog" (include "setupranali.fullname" .) }}
{{- end }}
{{- end }}

