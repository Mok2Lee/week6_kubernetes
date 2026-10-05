# 학생용 실습 안내

## 1. Kubernetes의 구성 요소

**목적:** 지난주 수동 컨테이너 실행과 Kubernetes 관리의 차이를 설명합니다.

이미지는 실행에 필요한 파일 묶음이고, 컨테이너는 이미지로 실행한 프로세스입니다. Kubernetes는 컨테이너를 Pod 단위로 배치하고 선언한 상태를 유지합니다. 이번 실습의 각 Pod에는 컨테이너 하나가 있습니다.

|개념|역할|이번 실습|
|---|---|---|
|클러스터|여러 노드를 함께 관리하는 단위|Minikube의 week6 프로필|
|Node|Pod를 실행하는 컴퓨터 환경|Docker 안에서 실행하는 학습용 노드|
|Control Plane|API 요청·상태 저장·배치·제어|API Server, etcd, Scheduler, Controller Manager|
|kubelet / 런타임|노드에서 Pod 상태 보고 / 컨테이너 실행|노드 내부에서 동작|
|Pod|Kubernetes의 최소 배포 단위|Flask Pod, nginx Pod|
|Deployment|Pod 템플릿·복제 수·업데이트 관리|api, web|
|Service|선택한 Pod로 접근하는 안정된 주소|api:5000, web:80|

`kubectl apply`는 API Server에 원하는 상태를 전달합니다. 컨트롤러가 실제 상태와 비교하고 Scheduler가 노드를 고릅니다. kubelet과 런타임이 컨테이너를 실행합니다. Pod 삭제 후 새 Pod를 만드는 것은 자동 복구이며, 요청량에 따라 복제 수를 자동 조절하는 HPA와 다릅니다. 이번 기본 실습의 scale은 **수동 확장**입니다.

**확인:** Pod와 이미지는 같은 것인가요? Pod 3개를 선언했는데 1개가 삭제되면 Deployment는 무엇을 해야 하나요?

## 2. 실행 환경과 새 저장소

**목적:** 지난주 작업과 분리된 폴더에서 시작합니다.

Docker Desktop을 실행하고 Linux 컨테이너 엔진 준비를 기다립니다. [교수자 저장소](https://github.com/Mok2Lee/week6_practice)를 본인 계정으로 Fork합니다. 아래 `내계정`을 실제 GitHub 계정으로 바꾸고 **본인 작업 폴더**에서 실행합니다.

```powershell
git clone https://github.com/내계정/week6_practice.git week6
Set-Location .\week6
code .
Get-Location
Get-ChildItem
docker version
docker compose version
```

**예상 결과·검증:** api, nginx, k8s 폴더와 compose.yaml이 보이고 Docker의 Client·Server 버전이 모두 나옵니다. VS Code 터미널 종류는 PowerShell입니다. Minikube를 시작한 뒤 제공되는 kubectl을 연결합니다.

**오류 해결:** Server가 없으면 Docker Desktop 상태를 확인합니다. 경로가 잘못되면 VS Code에서 week6 폴더를 다시 열어 터미널을 만듭니다. 같은 폴더에 다시 clone하지 않습니다. 8080 사용 여부는 `docker ps`와 `Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue`로 확인합니다. 다른 프로젝트 자원은 삭제하지 않습니다.

## 3. 이미지 생성과 Compose 복습

**목적:** 소스, 이미지, 실행 중인 컨테이너를 다시 구분합니다. Flask는 이미지 안에 설치되므로 Windows에 별도로 설치할 필요가 없습니다.

```powershell
docker build -t week6_01 ./api
docker build -t week6_02 ./nginx
docker image ls
docker compose config
docker compose up -d
docker compose ps
curl.exe -i http://localhost:8080/api/health
```

**예상 결과:** 두 이미지가 있고 컨테이너가 실행됩니다. health 응답은 HTTP 200, `status: ok`, `version: v1`, 컨테이너 이름을 나타내는 `pod`입니다.

브라우저 `http://localhost:8080`에서 프로젝트 검색과 소개글 분량 검사를 실행합니다. 이전과 같은 기능입니다. nginx는 `/api/` 요청을 Compose의 `api:5000`으로 전달합니다. `proxy_pass` 주소 끝에 `/`를 붙이지 않아 Flask의 `/api/` 경로를 보존합니다.

**검증:** 검색 결과가 표시되고 100~300자 글의 분량 판정이 정상인지 확인합니다.

```powershell
docker compose logs --tail 10 api nginx
```

**확인:** Dockerfile에 학교 실습용 pip trusted-host 옵션을 기본 반영했습니다. 별도 Dockerfile을 선택하지 않습니다. 502이면 api 로그와 컨테이너 상태를 확인하고 API 준비 후 다시 요청합니다. 이미지 다운로드 오류와 pip 패키지 오류를 구분합니다.

**단계 정리:** Kubernetes에서 8080을 사용할 수 있도록 Compose 컨테이너·네트워크를 종료합니다. 이미지는 남습니다.

```powershell
docker compose down
```

## 4. Minikube 준비

**목적:** 로컬 PC에 학습용 Kubernetes 클러스터를 만듭니다. Docker Desktop 내장 Kubernetes는 켜지 않아도 됩니다.

[공식 Windows 설치 안내](https://minikube.sigs.k8s.io/docs/start/)에서 Minikube를 설치합니다. 학교에서 제공한 검증된 설치 파일을 사용할 수도 있습니다. 설치 후 새 PowerShell 터미널을 열어 `minikube version`을 확인합니다. winget이 준비된 PC의 공식 설치 명령은 다음과 같습니다.

```powershell
winget install Kubernetes.minikube
```

다운로드가 막히면 브라우저 보안 경고를 넘기지 말고 교수자에게 오류와 다운로드 도메인을 전달합니다. 이미 설치되어 있으면 설치 단계를 반복하지 않습니다. 2 CPU 이상, 여유 메모리 2GB 이상, 디스크 20GB 이상이 필요합니다. 아래 실습은 노드에 메모리 3GB를 지정합니다. Windows와 Docker Desktop이 쓸 여유 공간도 남겨 둡니다.

|옵션|의미|수업 설정|
|---|---|---|
|`--cpus=2`|Minikube 노드가 사용할 CPU 수|2개|
|`--memory=3072`|Minikube 노드가 사용할 메모리(MB)|약 3GB|
|`--driver=docker`|Docker 안에 학습용 노드 구성|Docker Desktop 사용|

8GB PC에서는 다른 앱을 닫고 가용 메모리를 확인합니다. 16GB 이상 PC도 이번 앱에는 CPU 2개·메모리 3GB부터 시작하면 됩니다. 메모리가 부족한 PC에서 숫자만 늘리면 호스트도 느려질 수 있습니다. **노드 전체 자원**이며 Pod 하나마다 이만큼 배정하는 옵션은 아닙니다.

```powershell
minikube version
minikube profile week6
minikube start --driver=docker --cpus=2 --memory=3072
minikube status
function kubectl { minikube kubectl -- @args }
kubectl config current-context
kubectl get nodes
kubectl cluster-info
```

**예상 결과·검증:** week6 노드가 `Ready`입니다. 처음 실행할 때 노드 이미지·Kubernetes 구성요소를 다운로드하므로 시간이 걸립니다. 처음 한 번 `minikube profile week6`로 실습용 클러스터를 선택합니다. 이후 같은 터미널에서 짧은 명령을 사용합니다. `kubectl config current-context` 결과가 week6인지 확인하고 진행합니다.

Docker Desktop에 포함된 kubectl이 새 Kubernetes보다 오래될 수 있습니다. 위 함수는 **현재 PowerShell 터미널에서만** Minikube가 제공하는 맞는 kubectl을 호출합니다. OS·PATH·PowerShell 프로필을 저장 변경하지 않습니다. 처음 호출할 때 호환되는 kubectl을 내려받을 수 있습니다. **새 터미널 B에서도 함수 한 줄을 다시 실행**합니다. 터미널을 닫으면 함수는 사라집니다. `kubectl version --client`로 버전을 확인합니다.

**오류 해결:** 메모리가 부족하면 실행 중인 프로그램과 Docker Desktop/WSL 자원 상태를 확인합니다. 첫 클러스터 생성에는 Kubernetes 이미지 다운로드가 필요합니다. 패키지용 trusted-host는 이 다운로드까지 해결하지는 않습니다. `minikube logs --problems`로 원인을 확인합니다.

## 5. 기본 명령과 첫 nginx

**목적:** kubectl의 `명령 리소스 이름 옵션` 구조를 익힙니다. 이미 만든 web 이미지를 노드에 전달해 추가 nginx 다운로드를 줄입니다.

```powershell
minikube image load week6_01
minikube image load week6_02
minikube image ls
kubectl get pods
```

**예상 결과:** 새 실습 프로필이라면 `No resources found`입니다. 이미지는 호스트 Docker에만 있으면 노드가 사용할 수 없으므로 반드시 load합니다. 단독 nginx 이미지로 별도 Deployment를 추가하는 대신 다음 단계에서 지난주 nginx와 Flask를 함께 배포합니다. 이렇게 하면 첫 요청부터 동일한 화면·기능을 확인할 수 있습니다.

|명령|읽는 내용|
|---|---|
|get|리소스 목록과 상태|
|describe|설정·이벤트와 실패 원인|
|logs|컨테이너가 출력한 로그|
|apply -f|YAML의 원하는 상태 반영|
|delete|지정한 리소스 삭제|

**확인:** YAML 들여쓰기는 공백으로 유지합니다. `get all`은 모든 종류의 리소스를 빠짐없이 보여주는 명령이 아닙니다.

## 6. Deployment와 Service 배포

**목적:** Compose의 api·nginx 역할을 Kubernetes Deployment·Service로 옮깁니다.

VS Code에서 `k8s/api.yaml`과 `k8s/web.yaml`을 엽니다. `---`는 한 파일 안의 두 리소스를 구분합니다. `replicas`는 원하는 Pod 수, `template`은 새 Pod의 설계도입니다. Deployment selector와 Pod label, Service selector가 같아야 연결됩니다. `imagePullPolicy: Never`는 이번 로컬 실습에서 원격 pull을 하지 않도록 합니다.

먼저 API Service와 Pod를 준비한 뒤 nginx를 시작합니다.

```powershell
kubectl apply -f ./k8s/api.yaml
kubectl rollout status deployment/api --timeout=120s
kubectl apply -f ./k8s/web.yaml
kubectl rollout status deployment/web --timeout=120s
kubectl get "deployments,pods,services"
kubectl get endpointslices
```

**예상 결과·검증:** Deployment 두 개가 `1/1`, Pod 두 개가 `1/1 Running`입니다. Service api 포트는 5000, web 포트는 80입니다. `containerPort`는 포트 정보를 선언하며, 실제로 앱이 그 포트에서 수신해야 합니다. `readinessProbe`를 통과한 Pod가 Service의 트래픽 대상이 됩니다.

**오류 해결:** `ErrImageNeverPull`이면 태그와 `minikube image ls`를 확인하고 다시 load합니다. `CrashLoopBackOff`이면 `kubectl logs deployment/api --previous` 또는 해당 web 로그를 확인합니다. `Pending`은 describe 이벤트에서 자원 부족을 확인합니다.

## 7. Service 접속과 기능 확인

**목적:** Pod IP가 달라져도 Service 이름을 사용해 연결합니다.

현재 터미널 A에서 아래 명령을 실행한 채 유지합니다.

```powershell
kubectl port-forward service/web 8080:80
```

**예상 결과:** `Forwarding from 127.0.0.1:8080 -> 80`. 새 PowerShell 터미널 B를 열고 week6 폴더에서 실행합니다.

```powershell
function kubectl { minikube kubectl -- @args }
curl.exe -i http://localhost:8080/api/health
curl.exe -s "http://localhost:8080/api/projects?category=web"
kubectl logs deployment/api --tail=10
```

브라우저에서도 검색·분량 검사를 다시 실행합니다. 요청 경로는 브라우저 8080 → port-forward → web Pod nginx 80 → api Service 5000 → api Pod Flask 5000입니다.

**검증:** health의 `pod` 값이 Kubernetes api Pod 이름인지 `get pods`와 대조합니다. `port-forward service/web`는 선택한 Pod 하나에 터널을 연결하므로 web 복제본의 부하 분산 실험으로 사용하지 않습니다. 이번 구성에서 nginx가 api Service로 보내는 요청은 여러 준비된 API Pod로 전달될 수 있지만, 순서·균등 분배를 보장하지 않습니다.

**오류 해결:** 터미널 A가 종료되면 접속도 끊깁니다. web Pod 교체 후에는 명령을 다시 실행합니다. 8080이 이미 사용 중이면 Compose가 종료됐는지 확인합니다. 502는 api Service selector와 endpointslices, API 로그를 점검합니다.

## 8. 복제본 확대와 자동 복구

**목적:** 원하는 Pod 수와 실제 Pod 수를 비교합니다. 아래 명령은 터미널 B에서 실행합니다.

```powershell
kubectl scale deployment/api --replicas=3
kubectl rollout status deployment/api --timeout=120s
kubectl get pods -l app=api -o wide
1..8 | ForEach-Object { curl.exe -s http://localhost:8080/api/health }
$pod = kubectl get pods -l app=api -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod
kubectl get pods -l app=api -w
```

**예상 결과·검증:** 기존 이름의 Pod가 삭제되고 새 이름의 Pod가 생성됩니다. 최종적으로 api Pod 3개가 준비됩니다. 삭제 전후 이름을 기록하고 **새 Pod 생성**과 **기존 컨테이너 재시작**을 구분합니다. 관찰 종료는 `Ctrl+C`입니다. 짧은 전환 중 요청 실패가 있을 수 있으므로 무중단을 단정하지 않습니다.

**오류 해결:** Pod 수가 1개로 돌아오면 `api.yaml`의 `replicas: 1`을 다시 apply했는지 확인합니다. 이번 scale은 명령으로 실제 원하는 상태를 바꿉니다. YAML에도 3을 기록하려면 직접 수정하고 apply합니다. 이후 실습에서는 3을 유지해도 됩니다.

## 9. 이미지 업데이트와 롤백

**목적:** 새 이미지 week6_03에 v2 표시를 넣고 교체를 관찰합니다. week6_01은 되돌리기용으로 남겨 둡니다.

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

**예상 결과·검증:** 교체 완료 후 version은 v2, 되돌린 후 v1입니다. Pod 이름도 바뀝니다. `rollout undo`는 Pod 템플릿의 이전 revision으로 돌아가며 데이터나 코드 파일을 되돌리는 Git 명령이 아닙니다. `set image`는 로컬 YAML 파일을 수정하지 않습니다. v2를 최종 상태로 보존하려면 YAML의 image도 맞춰야 합니다.

교체 직후에는 종료 중인 이전 Pod가 잠깐 응답할 수 있습니다. 이전 version이 나오면 잠시 후 health를 다시 확인하고, `kubectl get pods -l app=api`에서 이전 Pod가 종료됐는지 확인합니다.

Kubernetes 버전에 따라 rollback이 `last-applied-configuration`을 갱신하지 않는다는 경고가 나올 수 있습니다. 롤백 후에는 YAML의 image와 replicas를 의도한 최종 상태에 맞추고, 다음 apply가 무엇을 바꿀지 확인합니다. 실습에서는 v1 복원을 확인한 뒤 이번 YAML로 만든 자원만 정리합니다.

**오류 해결:** v2를 load하지 않으면 `ErrImageNeverPull`입니다. 이미지 load 후 rollout 상태를 다시 확인합니다. v1과 v2는 같은 기본 Dockerfile을 사용합니다.

## 10. 정리와 재시작

**목적:** 이번 실습 자원만 정리합니다. 먼저 결과를 기록합니다.

터미널 A에서 `Ctrl+C`로 port-forward를 종료합니다. 터미널 B에서 실행합니다.

```powershell
kubectl delete -f ./k8s/
kubectl get deployments api web
minikube stop
docker compose down
```

**예상 결과:** api와 web Deployment 조회가 `NotFound`이고 week6 프로필은 중지됩니다. 이 YAML에 정의한 두 Deployment와 두 Service만 삭제합니다.

다음 시간에 다시 시작하려면 `minikube start --driver=docker` 후 5~7단계를 실행합니다. 이번 프로필이 더 필요 없으면 `minikube delete`로 삭제할 수 있습니다. 이 명령은 **week6 프로필 안의 모든 데이터**를 삭제합니다. 이미지까지 정리하려면 이번 태그만 지정합니다.

```powershell
docker image rm week6_01 week6_03 week6_02
```

없는 태그는 오류가 날 수 있습니다. 다른 이미지나 다른 학생의 자원을 삭제하지 않습니다.

## 공식 참고

- [Minikube 시작](https://minikube.sigs.k8s.io/docs/start/), [로컬 이미지 전달](https://minikube.sigs.k8s.io/docs/handbook/pushing/)
- [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
- [port-forward](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
