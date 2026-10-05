# 6주차 Kubernetes 실습

지난주 Flask·nginx의 기능을 **Compose 요청 발생기 → Kubernetes API**로 연결합니다. 요청량을 바꾸고, 요청이 여러 Pod에 분산되며 Pod 수가 자동으로 달라지는 과정을 확인합니다.

## 1. 작업 폴더 준비

Docker Desktop을 실행하고 **Linux 컨테이너**가 준비될 때까지 기다립니다. 교수자가 접근 권한을 제공한 week6_practice를 본인 계정으로 Fork한 뒤, 본인 작업 폴더에서 실행합니다. `내계정`을 실제 GitHub 계정으로 바꿉니다.

```powershell
git clone https://github.com/내계정/week6_practice.git week6
Set-Location .\week6
code .
docker version
docker compose version
minikube version
```

**확인:** Docker의 Client·Server가 모두 표시되고 `api`, `nginx`, `metrics`, `sender`, `k8s`, `scripts` 폴더가 보입니다. VS Code 터미널은 **PowerShell**을 사용합니다. 기존 week5 폴더는 이번 작업 폴더와 구분합니다.

Minikube는 수업에서 제공한 설치 파일을 사용합니다. 설치 후 새 터미널을 엽니다. Flask·Python은 이미지 안에 설치하므로 Windows에 별도로 설치하지 않습니다.

## 2. Minikube 시작

```powershell
minikube profile week6
minikube start --driver=docker --cpus=2 --memory=3072
function kubectl { minikube kubectl -- @args }
kubectl config current-context
kubectl version
kubectl get nodes
```

**확인:** 현재 연결은 `week6`, 노드는 `Ready`입니다. Server Version은 **Kubernetes 1.35 이상**이어야 합니다. 제공된 HPA의 `tolerance` 설정을 사용하기 위한 조건입니다. 낮은 버전이면 다음 단계 전에 교수자에게 확인합니다.

| 옵션 | 의미 |
| --- | --- |
| `--driver=docker` | Docker 안에 학습용 노드 구성 |
| `--cpus=2` | 노드 전체에서 사용할 CPU 2개 |
| `--memory=3072` | 노드 전체에서 사용할 메모리 약 3GB |

CPU·메모리 옵션은 **Pod 하나의 자원**이 아닙니다. Windows와 Docker Desktop이 사용할 여유 자원도 필요합니다. 처음 시작할 때 노드 이미지 다운로드가 필요할 수 있습니다.

`kubectl` 함수는 현재 터미널에서 Minikube에 맞는 명령을 연결합니다. **새 PowerShell 터미널에서도 함수 한 줄을 다시 실행**합니다.

## 3. 이미지 생성과 전달

week6 폴더에서 실행합니다.

```powershell
docker build -t week6_01 ./api
docker build -t week6_02 ./nginx
docker build -t week6_04 ./metrics
minikube image load week6_01
minikube image load week6_02
minikube image load week6_04
minikube image ls
```

**확인:** 세 이미지가 Minikube 이미지 목록에 보입니다.

| 이미지 | 역할 |
| --- | --- |
| `week6_01` | Flask 기능 API |
| `week6_02` | nginx 대시보드·API 전달 |
| `week6_04` | 요청 수 집계·HPA 지표 연결 |

호스트 Docker에서 만든 이미지는 `image load`로 노드에 전달해야 합니다. Dockerfile에는 학교용 pip 옵션이 들어 있습니다. 별도 Dockerfile을 선택하지 않습니다.

## 4. 지표 연결과 Kubernetes 배포

먼저 제공된 설정 파일을 실행합니다. 학생이 인증서나 지표 서버를 직접 작성할 필요는 없습니다.

```powershell
& .\scripts\setup-metrics.ps1
kubectl apply -f ./k8s/
kubectl rollout status deployment/api --timeout=120s
kubectl rollout status deployment/web --timeout=120s
kubectl rollout status deployment/metrics --timeout=120s
kubectl get "deployments,pods,services,hpa"
```

**확인:** `api`, `web`, `metrics` Deployment가 준비되고 `api` HPA가 보입니다. 지표 연결 파일은 자동 생성됩니다. `.lab/`의 파일은 GitHub나 과제에 올리지 않습니다.

| 구성 | 이번 실습에서 하는 일 |
| --- | --- |
| Deployment | API·웹·지표 Pod 실행과 교체 관리 |
| Service | 이름으로 Pod에 연결하고 준비된 API Pod로 요청 전달 |
| HPA | 측정된 요청 수에 따라 API Pod 수 조절 |
| 지표 앱 | 최근 60초 요청을 합산해 HPA에 제공 |

HPA는 Kubernetes의 실제 자동 확장 기능입니다. **Pod 1개당 평균 분당 50건**은 이번 수업에서 정한 목표이며 서버의 실제 처리 한계를 뜻하지 않습니다. 최소 1개, 최대 5개로 설정되어 있습니다.

## 5. 대시보드 연결

**터미널 A**에서 실행하고 창을 유지합니다.

```powershell
kubectl port-forward service/web 8080:80
```

**확인:** `Forwarding from 127.0.0.1:8080 -> 80`이 표시됩니다. 브라우저에서 <http://localhost:8080>을 엽니다.

새 **터미널 B**를 week6 폴더에서 열고 실행합니다.

```powershell
function kubectl { minikube kubectl -- @args }
curl.exe -i http://localhost:8080/api/health
kubectl get pods -l app=api
```

**확인:** health가 HTTP 200이며 `status: ok`, `version: v1`을 반환합니다. 응답의 `pod` 이름을 목록과 비교합니다. health 확인은 요청량 지표에 포함되지 않습니다.

대시보드에서 **프로젝트 검색·소개글 검사** 링크를 열어 두 기능이 정상인지 확인합니다. 기본 대시보드는 요청 수, HPA가 정한 Pod 수, 준비된 Pod 수, API별·Pod별 처리 결과를 표시합니다.

## 6. Compose 요청 발생기 실행

**터미널 B**에서 실행합니다.

```powershell
Set-Location .\sender
docker compose up -d --build
docker compose ps
Set-Location ..
```

**확인:** `week5_sender01`이 실행됩니다. <http://localhost:8090>을 엽니다.

요청 발생기는 Compose로만 실행합니다. 대상은 PC의 8080 포트에 연결된 Kubernetes API입니다.

**요청 경로:** 발생기 → PC 8080 → nginx → api Service → 준비된 API Pod

요청할 API는 **프로젝트 검색** 또는 **소개글 분량 검사**입니다. 지난주 실제 기능에 요청을 보내며 마지막 기능 결과와 응답 Pod를 확인할 수 있습니다. 발생기는 최대 분당 250건으로 제한되어 있습니다.

## 7. 요청량에 따른 자동 확장 관찰

발생기에서 **프로젝트 검색**을 선택합니다. 슬라이더를 40에 맞추고 **요청 시작**을 누릅니다. 다음 순서대로 각 단계에서 **최소 90초** 관찰합니다.

| 슬라이더 설정 | 최근 60초 요청이 안정된 뒤 기대하는 API Pod |
| --- | --- |
| 40건/분 | 1개 |
| 120건/분 | 3개 |
| 220건/분 | 5개 |

각 단계에서 아래 항목을 기록합니다.

1. 발생기의 **설정값·최근 60초 성공 수·실패 수**
2. 대시보드의 **실제 최근 60초 요청 수**
3. **전체 요청량·현재 Pod 수·Pod당 평균 요청량·목표 50건**
4. **HPA가 정한 Pod 수·준비 완료 Pod 수**
5. **API별·Pod별 요청 수**와 평균 처리 시간

터미널 B에서도 확인합니다.

```powershell
kubectl get hpa api
kubectl get pods -l app=api
```

요청 수를 바꾸면 최근 60초에는 이전 요청량이 함께 포함됩니다. HPA 확인과 Pod 준비에도 시간이 필요합니다. **90초는 관찰 기준이며 결과를 보장하는 고정 시간은 아닙니다.** 아직 변하는 중이면 실제 측정값과 준비 상태가 안정될 때까지 더 기다립니다.

`kubectl get hpa`의 TARGETS가 `43800m/50 (avg)`처럼 보일 수 있습니다. 여기서 `m`은 천분의 일 표기이므로 **43800m = 43.8건/분**입니다. 이번 지표에서는 CPU가 아니라 Pod당 평균 요청량을 뜻합니다.

예를 들어 최근 60초 요청이 120건이고 현재 Pod가 1개라면 Pod당 평균은 120건입니다. 목표 50건보다 높으므로 HPA가 확장합니다. Pod가 3개가 되면 평균은 `120 ÷ 3 = 40건`입니다. **필요한 Pod 수**는 `120 ÷ 50`을 올림한 3개입니다. 220건에서는 5개가 필요하며 평균은 44건입니다. Pod별 실제 요청 수가 똑같을 필요는 없습니다.

요청 중 **소개글 분량 검사**로 API를 바꾸고 API별 표의 기록이 달라지는지도 확인합니다. 대시보드·health 조회는 합산에서 제외됩니다. 화면의 요청 수와 처리 시간은 실제 측정값이며 CPU 사용률은 표시하지 않습니다.

**HPA 실습 중에는 `kubectl scale`을 사용하지 않습니다.** 수동으로 바꾼 수를 HPA가 다시 조절할 수 있습니다.

## 8. Pod 삭제와 자동 복구

120건/분으로 요청을 보내고 Pod 3개가 준비될 때까지 기다립니다. 터미널 B에서 실행합니다.

```powershell
kubectl get pods -l app=api
$pod = kubectl get pods -l app=api -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod
kubectl get pods -l app=api -w
```

**확인:** 삭제한 Pod 이름이 사라지고 새 이름의 Pod가 생성됩니다. 준비 완료까지 관찰한 후 `Ctrl+C`로 목록 감시를 종료합니다. 발생기의 실패 건수도 확인합니다.

Deployment의 **삭제된 Pod 복구**와 HPA의 **요청량에 따른 개수 조절**을 구분합니다. 짧은 전환 중 요청이 실패할 수 있습니다. 이번 실습은 단일 노드이며 여러 서버의 장애 대응 시험은 아닙니다.

## 9. 이미지 업데이트와 롤백

week6 폴더에서 실행합니다. 기존 `week6_01`은 되돌리기용으로 남겨 둡니다.

```powershell
docker build --build-arg APP_VERSION=v2 -t week6_03 ./api
minikube image load week6_03
kubectl set image deployment/api api=week6_03
kubectl rollout status deployment/api --timeout=120s
curl.exe -s http://localhost:8080/api/health
kubectl rollout history deployment/api
kubectl rollout undo deployment/api
kubectl rollout status deployment/api --timeout=120s
curl.exe -s http://localhost:8080/api/health
```

**확인:** 업데이트 후 `version: v2`, 롤백 후 `version: v1`입니다. Pod 이름도 바뀝니다. 교체 직후 이전 Pod가 잠시 응답할 수 있으므로 이전 버전이 나오면 Pod 상태와 health를 다시 확인합니다.

`rollout undo`는 이전 Pod 템플릿으로 돌아가는 명령입니다. 소스 파일이나 데이터를 Git처럼 되돌리지 않습니다. `set image`는 로컬 YAML을 수정하지 않습니다.

## 10. 요청 중지와 정리

발생기에서 **요청 중지**를 누릅니다. 최근 60초 요청 수가 줄어드는 과정과 Pod 수가 최소 1개로 돌아오는 과정을 기록합니다. 집계 구간과 축소 대기 시간 때문에 **90초보다 오래 걸릴 수 있습니다**.

터미널 A에서 `Ctrl+C`로 port-forward를 종료합니다. 터미널 B의 week6 폴더에서 실행합니다.

```powershell
Set-Location .\sender
docker compose down
Set-Location ..
& .\scripts\cleanup.ps1
minikube stop
```

**확인:** 이번 요청 발생기가 종료되고 week6 실습 자원이 정리됩니다. 다른 프로젝트의 컨테이너나 이미지를 함께 삭제하지 않습니다.

## 오류 확인 순서

| 증상 | 먼저 확인할 것 |
| --- | --- |
| Docker Server가 표시되지 않음 | Docker Desktop 실행과 Linux 엔진 준비 |
| `ErrImageNeverPull` | 이미지 이름·빌드 성공·`minikube image load` |
| `Pending`·`CrashLoopBackOff` | `kubectl describe pod Pod이름`의 Events, `kubectl logs deployment/api` |
| 대시보드 접속 실패 | 터미널 A의 port-forward와 8080 사용 여부 |
| 발생기 연결 실패 | week6 배포·8080 연결·발생기의 실패 안내 |
| 요청은 늘지만 HPA 지표가 `<unknown>` | `kubectl describe hpa api`, `kubectl logs deployment/metrics` |
| 목표 Pod 수와 준비 수가 다름 | Pod 생성·준비 상태를 확인하고 잠시 기다리기 |

오류가 생기면 **오류 화면과 해당 명령의 결과**를 함께 확인합니다. 지표 앱이 재시작하면 수업용 집계는 초기화됩니다.

## 다음 단계

기본 실습 뒤 [관리 기초](management-basics.md)에서 상태·로그·이벤트·설정·권한·저장소 관리의 역할을 정리하고 [추가 과제](assignment.md)를 진행합니다.

공식 참고: [Minikube 시작](https://minikube.sigs.k8s.io/docs/start/), [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Service](https://kubernetes.io/docs/concepts/services-networking/service/), [HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
