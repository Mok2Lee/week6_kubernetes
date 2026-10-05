# 6주차 Kubernetes 실습

**Compose 요청 발생기**에서 요청량을 바꾸고, **Kubernetes API**의 Pod 수가 달라지는 과정을 관찰합니다. 학교와 집에서 같은 제공 파일과 같은 명령을 사용합니다.

## 1. 실습 파일 준비

학교 NAS에서 제공한 파일을 아래 위치에 준비합니다. ZIP을 풀었을 때 같은 이름의 폴더가 한 번 더 중첩되지 않도록 확인합니다.

| 위치 | 확인할 파일 |
| --- | --- |
| `C:\lab\week6` | `api`, `nginx`, `metrics`, `k8s`, `README.md` |
| `C:\lab\week6_sender` | `app.py`, `static`, `compose.yaml` |
| `C:\lab\tools` | `minikube.exe`, `kubectl.exe` |
| `C:\lab\offline` | `week6_images.tar` |
| `%USERPROFILE%\.minikube\cache` | 교수자가 제공한 Minikube 캐시의 내용 |

탐색기 주소창에 `%USERPROFILE%\.minikube`를 입력하면 내 계정의 Minikube 폴더를 엽니다. 없다면 폴더를 만든 뒤 제공된 `cache` 폴더를 넣습니다. 최종 경로가 `.minikube\cache\cache`로 중첩되지 않도록 합니다. 다른 실습에 쓰던 `.minikube` 폴더 전체를 삭제하지 않습니다.

캐시는 **제공된 Minikube 버전·Kubernetes v1.35.0·containerd**에 맞춘 파일입니다. 다른 버전의 파일을 섞지 않습니다. 최초 실행에 필요한 이미지나 캐시가 누락되면 다운로드를 시도할 수 있으므로 교수자가 제공한 묶음을 모두 준비합니다.

GitHub에서 받을 수 있는 환경에서는 교수자가 안내한 두 저장소를 본인 계정으로 Fork한 뒤 아래처럼 내려받아도 됩니다. `내계정`을 실제 계정으로 바꿉니다. 이미 제공 ZIP을 풀었다면 아래 복제 과정은 건너뜁니다.

```powershell
cd C:\lab
git clone https://github.com/내계정/week6_practice.git week6
git clone https://github.com/내계정/week6_sender.git week6_sender
```

## 2. 명령 실행 환경 준비

Docker Desktop을 실행하고 **Linux 컨테이너**가 준비될 때까지 기다립니다. 다음 Path 등록은 PC에서 한 번만 합니다.

1. Windows에서 **환경 변수**를 검색하고 **사용자 환경 변수 편집**을 엽니다.
2. 사용자 변수의 **Path → 편집 → 새로 만들기**를 선택합니다.
3. `C:\lab\tools`를 추가하고 저장합니다. 기존 항목은 지우지 않습니다.
4. VS Code를 완전히 닫았다가 다시 엽니다.
5. **폴더 열기**로 `C:\lab\week6`를 엽니다.
6. **터미널 → 새 터미널**에서 PowerShell을 열고 이름을 **A — 실습 관리**로 바꿉니다.

이후 별도 표시가 없는 명령은 모두 **터미널 A**에서 실행합니다. 새 터미널 B는 7단계에서 만듭니다.

```powershell
cd C:\lab\week6
Get-Command minikube
Get-Command kubectl
docker version
docker compose version
minikube version
kubectl version --client
```

**확인:** 두 명령의 실행 경로가 제공 도구를 가리키고, Docker의 **Client·Server**가 모두 표시됩니다. Flask·Python은 Windows에 따로 설치하지 않습니다.

## 3. 제공 이미지 불러오기

**터미널 A**에서 실행합니다.

```powershell
docker load -i C:\lab\offline\week6_images.tar
docker image ls
```

**확인:** 아래 실습 이미지가 표시됩니다. Minikube 자체의 시작 파일은 앞에서 복사한 `cache` 폴더에 들어 있습니다.

| 이미지 | 역할 |
| --- | --- |
| `week6_01` | Flask 기능 API v1 |
| `week6_02` | nginx 대시보드·API 전달 |
| `week6_03` | 추가 실습용 API v2 |
| `week6_04` | 요청 수 집계·HPA 지표 연결 |
| `week6_sender01` | Docker Compose 요청 발생기 |

수업에서는 제공된 이미지를 사용합니다. `docker build`와 `pip install`은 실행하지 않습니다.

## 4. Minikube 시작

**터미널 A**에서 실행합니다.

```powershell
minikube profile week6
minikube profile
minikube start --driver=docker --container-runtime=containerd `
  --kubernetes-version=v1.35.0 --cpus=2 --memory=3072
kubectl config current-context
minikube status -p week6
kubectl version
kubectl get nodes
```

**확인:** 프로필과 현재 연결은 **week6**, Kubernetes Server Version은 **v1.35.0**, 노드는 **Ready**입니다. Minikube의 host·kubelet·apiserver는 Running이어야 합니다.

`start` 명령의 두 줄을 함께 복사합니다. 첫 줄 끝의 **백틱**은 명령이 다음 줄로 이어진다는 표시입니다.

| 옵션 | 의미 |
| --- | --- |
| `--driver=docker` | Docker 안에 학습용 노드 구성 |
| `--container-runtime=containerd` | 제공 캐시와 같은 컨테이너 실행 방식 사용 |
| `--kubernetes-version=v1.35.0` | 제공 캐시와 같은 Kubernetes 버전 사용 |
| `--cpus=2` | 노드 전체에 CPU 2개 사용 |
| `--memory=3072` | 노드 전체에 메모리 약 3GB 사용 |

CPU·메모리 옵션은 Pod 하나의 자원이 아닙니다. Windows와 Docker Desktop이 사용할 여유 자원도 필요합니다. 버전이나 인증서 오류가 나오면 다음 배포 단계로 넘어가지 말고 아래 오류 확인을 따릅니다.

## 5. Minikube에 앱 이미지 전달

PC Docker에 불러온 이미지를 **Minikube 노드**에도 전달합니다. **터미널 A**에서 실행합니다.

```powershell
minikube image load week6_01
minikube image load week6_02
minikube image load week6_03
minikube image load week6_04
minikube image ls
```

**확인:** `week6_01`부터 `week6_04`까지 Minikube 이미지 목록에 보입니다. 발생기 이미지 `week6_sender01`은 PC Docker에서 사용하므로 노드에 전달하지 않습니다.

## 6. Kubernetes 배포

**터미널 A / C:\lab\week6**에서 실행합니다. 제공된 지표 앱이 요청량을 HPA에 연결합니다.

```powershell
kubectl apply -f ./k8s/
kubectl rollout status deployment/metrics --timeout=120s
kubectl rollout status deployment/api --timeout=120s
kubectl rollout status deployment/web --timeout=120s
kubectl get "deployments,pods,services,hpa"
```

**확인:** `api`, `web`, `metrics` Deployment가 준비되고 `api` HPA가 보입니다. 지표가 준비되는 동안 TARGETS가 잠시 `<unknown>`이면 조금 기다렸다가 `kubectl get hpa api`로 다시 확인합니다.

HPA 기준은 **Pod 1개당 평균 분당 50건**이며 최소 1개, 최대 5개입니다. 50건은 학습용 목표이며 서버의 실제 처리 한계를 뜻하지 않습니다.

## 7. 대시보드 연결

VS Code 터미널의 **+**로 새 PowerShell을 한 개 열고 이름을 **B — 대시보드 연결**로 바꿉니다. **터미널 B**에서만 아래 명령을 실행합니다.

```powershell
cd C:\lab\week6
kubectl port-forward service/web 8080:80
```

**확인:** `Forwarding from 127.0.0.1:8080 -> 80`이 표시됩니다. 브라우저에서 <http://localhost:8080>을 엽니다. **B는 종료하지 않고 그대로 둡니다.** 다른 명령은 A에서 실행합니다.

**터미널 A**를 선택하고 확인합니다.

```powershell
curl.exe -i http://localhost:8080/api/health
kubectl get pods -l app=api
```

**확인:** health는 HTTP 200이며 `status: ok`, `version: v1`을 반환합니다. 응답의 `pod` 이름을 목록과 비교합니다. health 요청은 요청량 지표에 포함되지 않습니다.

대시보드의 **프로젝트 검색·소개글 검사** 링크를 열어 두 기능도 확인합니다.

| 터미널 | 현재 폴더 | 이후 사용 방법 |
| --- | --- | --- |
| A — 실습 관리 | `C:\lab\week6` | 명령 입력·상태 확인·과제 적용 |
| B — 대시보드 연결 | `C:\lab\week6` | port-forward 실행 상태 유지 |

## 8. Compose 요청 발생기 실행

새 터미널을 만들거나 폴더를 옮기지 않습니다. **터미널 A / C:\lab\week6**에서 옆 폴더의 Compose 파일을 지정합니다.

```powershell
docker compose -f ../week6_sender/compose.yaml up -d --no-build --pull never
docker compose -f ../week6_sender/compose.yaml ps
```

**확인:** `week6_sender01`이 실행됩니다. <http://localhost:8090>을 엽니다. `--no-build --pull never`는 이미 불러온 이미지를 사용하고 새 이미지 생성·다운로드를 하지 않는 옵션입니다.

요청은 **발생기 → PC 8080 → nginx → api Service → 준비된 API Pod** 순서로 전달됩니다. API 기능은 **프로젝트 검색**과 **소개글 분량 검사**입니다.

## 9. 요청량과 자동 확장 관찰

발생기에서 **프로젝트 검색**을 선택하고 슬라이더를 40에 맞춘 뒤 **요청 시작**을 누릅니다. 다음 순서대로 각 단계에서 **최소 90초** 관찰합니다.

| 발생기 설정 | 실제 요청량이 안정된 뒤 이론적 API Pod 수 |
| --- | --- |
| 40건/분 | 1개 |
| 120건/분 | 3개 |
| 220건/분 | 5개 |

발생기의 **성공·실패 수**와 대시보드의 **최근 60초 요청 수·Pod당 평균·HPA 목표 수·Ready 수**를 기록합니다. 설정값과 실제 성공 요청량은 다를 수 있습니다.

**터미널 A**에서도 확인합니다.

```powershell
kubectl get hpa api
kubectl get pods -l app=api
```

90초는 관찰 기준이며 결과를 보장하는 시간은 아닙니다. 최근 60초 집계와 Pod 준비 때문에 수치가 계속 바뀌면 안정될 때까지 더 기다립니다. HPA의 `43800m/50 (avg)`는 **Pod당 평균 43.8건/분 / 목표 50건/분**을 뜻합니다. 여기서 `m`은 천분의 일이며 CPU 단위가 아닙니다.

예를 들어 실제 요청이 120건/분이면 `120 ÷ 50`을 올림한 **3개**가 이론적 목표입니다. Pod가 3개이면 평균은 40건/분입니다. Pod별 실제 처리량이 똑같을 필요는 없습니다.

요청 기능을 **소개글 분량 검사**로 바꾸고 API별 기록도 확인합니다. 성공한 두 기능 API 요청만 합산하며 health·대시보드 조회는 제외합니다. 실습 중 `kubectl scale`로 Pod 수를 강제로 바꾸지 않습니다.

## 10. HPA 기준 변경

VS Code에서 `k8s/hpa.yaml`의 `averageValue: "50"`을 **`averageValue: "75"`**로 바꾸고 저장합니다. `maxReplicas: 5`는 유지합니다.

**터미널 A**에서 실행합니다.

```powershell
kubectl apply -f ./k8s/hpa.yaml
kubectl get hpa api
```

발생기는 **220건/분**으로 유지합니다. 대시보드 목표가 75로 바뀌는지 확인하고, 축소 대기 후 Pod 수를 비교합니다. 이론적 목표는 `220 ÷ 75`를 올림한 **3개**입니다. 실제 요청량과 Ready 수가 안정된 결과를 기록합니다.

과제의 표와 제출 항목은 [과제 안내](assignment.md)를 따릅니다.

## 11. 요청 중지와 정리

1. 발생기 화면에서 **요청 중지**를 누릅니다.
2. 최근 60초 요청 수가 줄고 API Pod가 **최소 1개**로 돌아오는 과정을 확인합니다.
3. **터미널 A**에서 발생기를 종료합니다.

```powershell
docker compose -f ../week6_sender/compose.yaml down
```

4. **터미널 B**에서 `Ctrl+C`로 대시보드 연결을 종료합니다.
5. **터미널 A / C:\lab\week6**에서 수신 자원을 정리하고 Minikube를 멈춥니다.

```powershell
kubectl delete -f ./k8s/
minikube stop
```

**확인:** 발생기와 이번 실습 자원이 종료됩니다. 제공된 이미지·캐시는 다음 실행에 다시 사용하므로 지우지 않습니다.

## 추가 실습

기본 관찰을 마친 뒤 수업에서 안내한 경우 진행합니다. 정리 전에 수행하며 **과제 필수 항목은 아닙니다**. HPA 목표를 50으로 복원하고 적용한 뒤 시작합니다. 명령은 모두 **터미널 A**에서 실행합니다.

### Pod 삭제와 복구

발생기에서 120건/분으로 요청을 보내고 Pod 3개가 준비될 때까지 기다립니다.

```powershell
kubectl get pods -l app=api
kubectl delete pod 복사한Pod이름
kubectl get pods -l app=api -w
```

`복사한Pod이름`을 앞서 출력한 Pod 이름 하나로 바꿉니다. 새 이름의 Pod가 준비되면 **Ctrl+C**로 목록 감시를 끝냅니다. 발생기의 실패 건수도 확인합니다. Deployment의 **Pod 복구**와 HPA의 **개수 조절**을 구분합니다.

### 업데이트와 롤백

준비 단계에서 전달한 **week6_03**이 API v2 이미지입니다. 이미지를 새로 빌드하지 않습니다.

```powershell
kubectl set image deployment/api api=week6_03
kubectl rollout status deployment/api --timeout=120s
curl.exe -s http://localhost:8080/api/health
kubectl rollout history deployment/api
kubectl rollout undo deployment/api
kubectl rollout status deployment/api --timeout=120s
curl.exe -s http://localhost:8080/api/health
```

**확인:** 업데이트 후 `version: v2`, 롤백 후 `version: v1`입니다. 교체 직후 이전 Pod가 응답하면 잠시 기다린 뒤 다시 확인합니다. `rollout undo`는 이전 Pod 템플릿으로 돌아갑니다. 소스 파일이나 데이터를 Git처럼 되돌리는 명령은 아닙니다.

## 오류 확인

| 증상 | 확인할 내용 |
| --- | --- |
| `minikube`·`kubectl`을 찾지 못함 | `C:\lab\tools`의 파일, 사용자 Path, VS Code 재시작 |
| Docker Server가 표시되지 않음 | Docker Desktop 실행과 Linux 엔진 준비 |
| 시작 중 다운로드·SSL 인증서 오류 | 제공 버전·이미지·캐시 누락 여부를 확인하고 오류 화면을 교수자에게 전달 |
| `ErrImageNeverPull` | `docker load` 성공, 이미지 이름, `minikube image load` 완료 여부 |
| 발생기 이미지가 없다는 오류 | `docker image ls`에서 `week6_sender01` 확인 |
| Compose 파일을 찾지 못함 | A가 `C:\lab\week6`인지, 옆에 `week6_sender`가 있는지 확인 |
| `Pending`·`CrashLoopBackOff` | `kubectl describe pod Pod이름`의 Events와 `kubectl logs deployment/api` |
| 대시보드 접속 실패 | B의 port-forward 유지 여부와 8080 포트 확인 |
| 발생기 연결 실패 | 8080 대시보드와 API health, 발생기의 실패 안내 확인 |
| HPA의 `<unknown>`이 계속됨 | `kubectl describe hpa api`, `kubectl logs deployment/metrics` |
| Pod가 바로 줄지 않음 | 최근 60초 집계와 축소 대기 시간 고려 |

학교 PC의 실제 통신 정책은 수업 전 확인이 필요합니다. 제공 파일이 있어도 PC 설정이나 누락된 캐시 때문에 추가 준비가 필요할 수 있습니다. 인증서 검증을 끄거나 임의 패키지 다운로드로 우회하지 않습니다.

공식 참고: [Minikube 시작](https://minikube.sigs.k8s.io/docs/start/), [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Service](https://kubernetes.io/docs/concepts/services-networking/service/), [HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
