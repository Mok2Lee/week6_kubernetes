# 6주차 Kubernetes 실습

**요청 발생기는 Docker Compose**, **요청을 받는 API는 Kubernetes**로 실행합니다. 요청량을 바꾸며 API Pod 수가 달라지는 과정을 확인합니다.

## 1. 프로젝트와 터미널 준비

두 저장소를 C: 바로 아래에 준비합니다. 아래 명령은 두 프로젝트를 처음 받을 때 한 번 실행합니다. 본인 계정으로 Fork했다면 `Mok2Lee`를 본인 계정으로 바꿉니다.

```powershell
cd C:\
git clone https://github.com/Mok2Lee/week6_practice.git
git clone https://github.com/Mok2Lee/week6_kubernetes.git
```

Docker Desktop을 실행한 뒤, VS Code에서 각 프로젝트 폴더를 열고 PowerShell을 하나씩 엽니다.

| 터미널 | 작업 폴더 | 역할 |
| --- | --- | --- |
| **A — 요청 발생기** | `C:\week6_practice` | Compose 실행·로그 확인 |
| **B — Kubernetes** | `C:\week6_kubernetes` | Minikube·이미지 빌드·배포·HPA 확인 |

아래 단계부터는 표시된 터미널에서만 실행합니다.

## 2. 요청 발생기 실행 — 터미널 A

```powershell
cd C:\week6_practice
docker compose up
```

이미지를 빌드한 뒤 발생기를 시작합니다. <http://localhost:8090>이 열리는지 확인합니다. **A는 실행 상태로 둡니다.** API 배포가 끝난 뒤 요청을 시작합니다.

## 3. Minikube 시작 — 터미널 B

```powershell
cd C:\week6_kubernetes
minikube profile week6
minikube start --driver=docker --container-runtime=containerd `
  --ports=8080:30080 --kubernetes-version=v1.35.0 --cpus=2 --memory=3072
kubectl get nodes
```

**확인:** `week6` 노드가 **Ready**로 표시됩니다. `start` 명령의 두 줄을 함께 실행합니다. 첫 줄 끝의 **백틱**은 다음 줄까지 하나의 명령이라는 뜻입니다.

| 옵션 | 의미 |
| --- | --- |
| `--driver=docker` | Docker 안에 학습용 Kubernetes 노드 구성 |
| `--container-runtime=containerd` | 노드 안에서 컨테이너를 실행할 방식 지정 |
| `--ports=8080:30080` | PC의 8080 포트를 웹 Service의 30080 포트에 연결 |
| `--kubernetes-version=v1.35.0` | 이번 실습에서 사용할 Kubernetes 버전 지정 |
| `--cpus=2` | 노드 전체에 CPU 2개 사용 |
| `--memory=3072` | 노드 전체에 메모리 약 3GB 사용 |

이후 Kubernetes 명령은 계속 **터미널 B**에서 실행합니다.

## 4. 이미지 빌드 — 터미널 B

```powershell
docker build -t week6_01 ./api
docker build -t week6_02 ./nginx
docker build -t week6_04 ./metrics
docker image ls
```

| 이미지 | 역할 |
| --- | --- |
| `week6_01` | Flask 기능 API |
| `week6_02` | nginx 대시보드·API 요청 전달 |
| `week6_04` | 요청 수 집계·HPA 지표 전달 |

**확인:** 세 이미지가 목록에 표시됩니다. 인증서 오류가 발생하면 오류 화면을 교수자에게 전달합니다.

## 5. Minikube에 이미지 전달 — 터미널 B

PC Docker에서 만든 이미지를 **Minikube 노드에도 전달**합니다.

```powershell
minikube image load week6_01
minikube image load week6_02
minikube image load week6_04
```

요청 발생기는 PC Docker에서 실행하므로 Minikube에 전달하지 않습니다.

## 6. Kubernetes 배포 — 터미널 B

```powershell
kubectl apply -f ./k8s/
kubectl get "deployments,pods,services,hpa"
```

**확인:** `api`, `web`, `metrics` Deployment의 **READY가 1/1**, 각 Pod의 **STATUS가 Running**이 될 때까지 기다립니다. `api` HPA도 표시되어야 합니다. 잠시 후 같은 명령으로 다시 확인합니다.

## 7. 대시보드와 API 확인

브라우저에서 <http://localhost:8080>을 엽니다. 대시보드에서 **API Pod 수·최근 60초 요청 수·HPA 목표**를 확인합니다.

**터미널 B**에서 API도 확인합니다.

```powershell
curl.exe -i http://localhost:8080/api/health
```

**확인:** HTTP **200**, `status: ok`, `version: v1`, 응답한 `pod` 이름이 표시됩니다. health 요청은 부하 요청 수에 포함하지 않습니다.

대시보드의 **프로젝트 검색·소개글 검사** 링크를 열어 두 기능도 실행합니다.

요청은 **발생기 → PC 8080 → nginx → api Service → API Pod** 순서로 전달됩니다. 대시보드는 브라우저로 바로 열며, 추가 터미널은 만들지 않습니다.

## 8. 요청량과 자동 확장 관찰

<http://localhost:8090>에서 **프로젝트 검색**을 선택하고 요청량을 40으로 맞춘 뒤 **요청 시작**을 누릅니다.

| 요청량 설정 | 목표 50건/분일 때 이론적 API Pod 수 |
| --- | --- |
| 40건/분 | 1개 |
| 120건/분 | 3개 |
| 220건/분 | 5개 |

40 → 120 → 220 순서로 바꾸며 **각 단계에서 최소 90초** 관찰합니다. 실제 요청 수와 Ready Pod 수가 계속 바뀌면 안정될 때까지 더 기다립니다.

- 발생기: **성공·실패 요청 수** 확인
- 대시보드: **최근 60초 요청 수·Pod당 평균·목표 Pod 수·Ready 수** 확인

**터미널 B**에서도 상태를 확인합니다.

```powershell
kubectl get hpa api
kubectl get pods -l app=api
```

실제 요청량이 120건/분이면 `120 ÷ 50`을 올림한 **3개**가 이론적 목표입니다. 최소 1개·최대 5개 제한이 있으며, 요청량 집계와 Pod 준비 때문에 즉시 변하지는 않습니다.

HPA의 `43800m/50 (avg)`는 **Pod당 평균 43.8건/분 / 목표 50건/분**입니다. 여기서 `m`은 천분의 일이며 CPU 단위가 아닙니다.

기능을 **소개글 분량 검사**로 바꾸고 API별 요청 기록도 확인합니다. 성공한 두 기능 API 요청만 합산합니다.

## 9. HPA 기준 변경 — 터미널 B

`C:\week6_kubernetes\k8s\hpa.yaml`의 `averageValue: "50"`을 **`averageValue: "75"`**로 바꾸고 저장합니다. `maxReplicas: 5`는 유지합니다.

```powershell
kubectl apply -f ./k8s/hpa.yaml
kubectl get hpa api
```

발생기의 **220건/분**을 유지합니다. 대시보드 목표가 75로 바뀌는지 확인하고, 축소 대기 후 Pod 수를 비교합니다. 이론적 목표는 `220 ÷ 75`를 올림한 **3개**입니다.

기록할 표와 제출 내용은 [과제 안내](assignment.md)를 따릅니다.

## 10. 실습 종료

발생기 화면에서 **요청 중지**를 누릅니다. 최근 60초 요청 수가 줄고 API Pod가 최소 1개로 돌아오는 과정을 확인합니다.

**터미널 A:** `Ctrl+C`로 발생기를 멈춘 뒤 실행합니다.

```powershell
docker compose down
```

**터미널 B:** Kubernetes 실습 자원을 정리하고 Minikube를 멈춥니다.

```powershell
kubectl delete -f ./k8s/
minikube stop
```

## 추가 실습

수업에서 안내한 경우 **정리 전에** 진행합니다. 명령은 모두 **터미널 B**에서 실행합니다. 과제 필수 항목은 아닙니다.

### Pod 삭제와 복구

HPA 목표를 50으로 복원하고 적용합니다. 발생기에서 120건/분을 보내고 Pod 3개가 준비되면 실행합니다.

```powershell
kubectl get pods -l app=api
kubectl delete pod 복사한Pod이름
kubectl get pods -l app=api -w
```

`복사한Pod이름`은 목록에 나온 이름 하나로 바꿉니다. 새 Pod가 준비되면 **Ctrl+C**로 목록 감시를 끝냅니다. Deployment의 **Pod 복구**와 HPA의 **개수 조절**을 구분합니다.

### 이미지 업데이트와 롤백

API v2 이미지를 직접 빌드하고 Minikube에 전달합니다.

```powershell
docker build --build-arg APP_VERSION=v2 -t week6_03 ./api
minikube image load week6_03
kubectl set image deployment/api api=week6_03
kubectl rollout status deployment/api
curl.exe -s http://localhost:8080/api/health
```

**확인:** `version: v2`가 표시됩니다. 이전 버전으로 되돌립니다.

```powershell
kubectl rollout undo deployment/api
kubectl rollout status deployment/api
curl.exe -s http://localhost:8080/api/health
```

**확인:** `version: v1`이 표시됩니다. 롤백은 이전 Pod 설정으로 되돌리는 동작입니다.

## 실행 중 확인

| 증상 | 확인할 내용 |
| --- | --- |
| Compose 파일을 찾지 못함 | A의 현재 폴더가 `C:\week6_practice`인지 확인 |
| `ErrImageNeverPull` | 이미지 빌드와 `minikube image load` 완료 여부 확인 |
| `Pending`·`CrashLoopBackOff` | B에서 `kubectl describe pod Pod이름`, `kubectl logs deployment/api` 확인 |
| 대시보드가 열리지 않음 | `web` Pod의 Ready 상태와 시작 명령의 `--ports=8080:30080` 확인 |
| HPA의 `<unknown>`이 계속됨 | B에서 `kubectl describe hpa api`, `kubectl logs deployment/metrics` 확인 |
