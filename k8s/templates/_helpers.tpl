{{/*
Expand the name of the chart.
*/}}
{{- define "forge.name" -}}
{{- "forge" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "forge.fullname" -}}
{{- if contains "forge" .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name "forge" | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "forge.chart" -}}
{{- "forge" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "forge.labels" -}}
app.kubernetes.io/name: {{ include "forge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "forge.chart" . }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "forge.selectorLabels" -}}
app.kubernetes.io/name: {{ include "forge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
