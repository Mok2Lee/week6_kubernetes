param([string]$Image = 'week6_04')
$ErrorActionPreference = 'Stop'
$repoDirectory = Split-Path -Parent $PSScriptRoot
$certificateDirectory = Join-Path $repoDirectory '.lab'
$apiServiceName = 'v1beta1.external.metrics.k8s.io'

function Invoke-LabKubectl {
    & minikube kubectl -- @args
    if ($LASTEXITCODE -ne 0) { throw 'Kubernetes 명령 실행에 실패했습니다.' }
}

# 다른 클러스터의 통계 API를 바꾸지 않도록 실습 프로필을 확인합니다.
$profile = ((& minikube profile | Out-String).Trim() -replace '^\*\s*', '').Trim()
if ($LASTEXITCODE -ne 0 -or $profile -ne 'week6') {
    throw '먼저 minikube profile week6을 실행하세요.'
}
$context = (Invoke-LabKubectl config current-context | Out-String).Trim()
if ($context -ne 'week6') { throw '현재 Kubernetes 연결이 week6이 아닙니다.' }
$namespace = (Invoke-LabKubectl config view --minify -o 'jsonpath={..namespace}' | Out-String).Trim()
if ($namespace -and $namespace -ne 'default') {
    throw '실습 연결의 네임스페이스를 default로 설정하세요: kubectl config set-context --current --namespace=default'
}
$existing = (Invoke-LabKubectl get apiservice $apiServiceName --ignore-not-found -o json | Out-String).Trim()
if ($existing) {
    $object = $existing | ConvertFrom-Json
    if ($object.metadata.labels.'app.kubernetes.io/part-of' -ne 'week6-lab') {
        throw '다른 외부 지표 서비스가 이미 등록되어 있습니다. 덮어쓰지 않습니다.'
    }
}

New-Item -ItemType Directory -Path $certificateDirectory -Force | Out-Null
& docker run --rm --mount "type=bind,source=$certificateDirectory,target=/output" $Image python generate_certs.py /output
if ($LASTEXITCODE -ne 0) { throw '실습용 인증서를 생성하지 못했습니다. week6_04 이미지 빌드를 확인하세요.' }

$utf8 = New-Object System.Text.UTF8Encoding($false)
$secretPath = Join-Path $certificateDirectory 'metrics-secret.json'
$secret = @{
    apiVersion = 'v1'; kind = 'Secret'; type = 'kubernetes.io/tls'
    metadata = @{ name = 'metrics-tls'; namespace = 'default'; labels = @{ 'app.kubernetes.io/part-of' = 'week6-lab' } }
    data = @{
        'tls.crt' = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $certificateDirectory 'tls.crt')))
        'tls.key' = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $certificateDirectory 'tls.key')))
    }
}
[IO.File]::WriteAllText($secretPath, ($secret | ConvertTo-Json -Depth 8), $utf8)
Invoke-LabKubectl apply -f $secretPath --namespace default
Invoke-LabKubectl apply -f (Join-Path $repoDirectory 'k8s/metrics.yaml') --namespace default
Invoke-LabKubectl rollout restart deployment/metrics --namespace default
Invoke-LabKubectl rollout status deployment/metrics --namespace default --timeout=120s

$apiServicePath = Join-Path $certificateDirectory 'metrics-apiservice.json'
$apiService = @{
    apiVersion = 'apiregistration.k8s.io/v1'; kind = 'APIService'
    metadata = @{ name = $apiServiceName; labels = @{ 'app.kubernetes.io/part-of' = 'week6-lab' } }
    spec = @{
        group = 'external.metrics.k8s.io'; version = 'v1beta1'
        groupPriorityMinimum = 100; versionPriority = 100
        service = @{ namespace = 'default'; name = 'metrics'; port = 8443 }
        caBundle = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $certificateDirectory 'ca.crt')))
    }
}
[IO.File]::WriteAllText($apiServicePath, ($apiService | ConvertTo-Json -Depth 8), $utf8)
Invoke-LabKubectl apply -f $apiServicePath
Invoke-LabKubectl wait --for=condition=Available "apiservice/$apiServiceName" --timeout=120s
Invoke-LabKubectl get --raw '/apis/external.metrics.k8s.io/v1beta1/namespaces/default/api_requests_per_minute'
Write-Host '통계 지표 연결 완료. 이제 kubectl apply -f ./k8s/로 API와 HPA를 배포하세요.'
