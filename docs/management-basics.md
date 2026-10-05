# Kubernetes 관리 기초

이번 실습은 **Compose가 요청을 보내고, Kubernetes가 API Pod를 관리하는 과정**을 관찰합니다. 요청량·목표 Pod 수·준비된 Pod 수를 함께 확인합니다.

## 서비스를 운영할 때 하는 일

|상황|Kubernetes에서 확인하는 것|
|---|---|
|요청이 증가함|측정값에 맞춰 API Pod 수 조절|
|Pod가 종료됨|Deployment가 필요한 Pod 수를 다시 맞추는지 확인|
|새 버전을 배포함|새 Pod가 준비된 뒤 기존 Pod가 교체되는지 확인|
|응답이 실패함|상태·이벤트·로그·Service 연결 순서로 원인 확인|

이번 Minikube는 PC 한 대의 학습 환경입니다. Pod 확장과 복구를 실습하며, 여러 서버가 서로 장애를 대신하는 구성은 별도로 배웁니다. [Kubernetes 개요](https://kubernetes.io/docs/concepts/overview/)

## 구성 요소와 관리 항목

|구성 요소|학생이 이해할 내용|
|---|---|
|Node|Pod를 실행하는 서버. `Ready`와 자원 상태를 확인|
|Deployment|실행할 이미지와 목표 Pod 수를 선언|
|Pod|실제로 앱이 실행되는 단위. `Ready`·재시작·로그를 확인|
|Service|Pod가 바뀌어도 같은 이름과 포트로 접근하는 경로|
|requests|Pod 배치를 판단할 때 필요한 CPU·메모리 양|
|limits|컨테이너의 CPU·메모리 사용 상한|

CPU `100m`은 0.1 CPU, 메모리 `128Mi`는 128 MiB입니다. CPU 상한은 실행 속도를 제한할 수 있고, 메모리 상한을 넘으면 컨테이너가 종료될 수 있습니다. [자원 관리](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

## 요청량에 따른 Pod 확대

이 실습의 **50건/분은 학습용 기준**입니다. 실제 서비스의 처리 한계를 측정한 값은 아닙니다.

- 최근 60초에 성공적으로 처리한 기능 API 요청(HTTP 2xx)을 셉니다.
- 목표 Pod 수는 `올림(전체 요청 수 ÷ 50)`으로 계산합니다.
- 50건이면 1개, 51~100건이면 2개, 101~150건이면 3개를 목표로 합니다.
- 최솟값·최댓값과 축소 대기 시간을 적용합니다.
- `/api/health`와 대시보드 조회는 API 부하 요청 수에서 제외합니다.

**목표 수**와 **Ready 수**는 다를 수 있습니다. 새 Pod가 실행되고 상태 검사를 통과할 시간이 필요합니다. 요청을 멈춰도 최근 60초 요청이 바로 사라지지 않으므로 잠시 기다린 뒤 축소를 관찰합니다.

|자동 확장 방식|기준|
|---|---|
|CPU 기반 HPA|CPU 사용량을 CPU requests와 비교|
|이번 수업의 요청량 기반 HPA|API가 센 요청 수를 제공된 외부 지표 어댑터를 통해 확인|

**요청 수와 CPU 사용률은 서로 다른 값**입니다. 이번 실습은 CPU HPA 대신 **요청량 HPA**를 사용합니다. **어댑터**는 앱의 요청 수를 Kubernetes가 읽는 지표로 전달합니다. HPA는 `AverageValue: 50`을 기준으로 목표 Pod 수를 조절합니다. 측정 주기와 안정화 대기 때문에 화면 변화에는 시간이 걸립니다. [공식 HPA 설명](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)

## 상태 → 이벤트 → 로그 → 연결

기본 명령은 **터미널 A / `C:\lab\week6`**에서 실행합니다. 터미널 B는 대시보드 연결을 유지합니다.

```powershell
kubectl get nodes
kubectl get "deployments,pods,services"
kubectl get hpa
kubectl describe deployment api
kubectl describe pod 복사한Pod이름
kubectl logs deployment/api --tail=30
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl get endpointslices
```

`복사한Pod이름`은 `kubectl get pods`에 나온 이름으로 바꿉니다. `logs deployment/api`는 선택된 한 Pod의 로그이므로, 여러 Pod의 처리량을 비교할 때는 각 Pod 이름으로 확인합니다.

|화면에 보이는 상태|다음 확인|
|---|---|
|`Pending`|Node 자원 부족·배치 조건 확인|
|`ErrImageNeverPull`|제공 이미지 불러오기·이미지 이름·Minikube 이미지 전달 여부 확인|
|`CrashLoopBackOff`|앱 로그·실행 명령·환경 설정 확인|
|실행 중인데 `Ready`가 0|readiness 경로·포트·응답 확인|
|Pod는 준비됐는데 요청 실패|Service selector·포트·EndpointSlice 확인|

[앱 문제 해결](https://kubernetes.io/docs/tasks/debug/debug-application/)

## 앱 상태 검사

|검사|역할|
|---|---|
|readiness|지금 요청을 받아도 되는지 확인. 실패하면 Service 요청 대상에서 제외|
|liveness|앱이 멈췄는지 확인. 계속 실패하면 컨테이너 재시작|
|startup|앱이 처음 시작할 때 충분히 기다리는 검사|

`/api/health`가 있다는 것만으로 검사가 자동 연결되지는 않습니다. Pod 설정에 해당 경로·포트·주기를 지정해야 합니다. [상태 검사](https://kubernetes.io/docs/concepts/workloads/pods/probes/)

## 설정·권한·저장소

|구성|용도|
|---|---|
|ConfigMap|API 주소·기준값처럼 공개 가능한 설정을 코드와 분리|
|Secret|비밀번호·토큰 같은 민감한 설정을 분리|
|ServiceAccount|Pod가 Kubernetes API를 사용할 때의 신원|
|RBAC|신원별로 조회·변경 가능한 자원을 제한|
|PVC|Pod가 바뀌어도 사용할 저장 공간을 요청|

제공된 지표 앱에는 상태 조회와 HPA 지표 연결에 필요한 권한을 지정합니다. 실행 수는 HPA가 조절합니다. Secret의 base64 표현은 암호화가 아닙니다. Pod 메모리에 저장한 값은 Pod가 사라지면 없어지므로, 보존할 데이터는 저장소와 백업을 따로 설계합니다.

[ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/), [Secret](https://kubernetes.io/docs/concepts/configuration/secret/), [ServiceAccount](https://kubernetes.io/docs/concepts/security/service-accounts/), [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [PVC](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

## 관리 학습의 다음 단계

공식 관리자 자격 **CKA**는 클러스터 구성, 워크로드·배치, 서비스·네트워크, 저장소, 문제 해결을 다룹니다. 이 수업은 해당 관리 개념에 들어가기 위한 기초입니다. 클러스터 설치·업그레이드·백업·다중 서버 구성과 심화 보안은 추가 실습이 필요합니다. [CNCF CKA 안내](https://www.cncf.io/training/certification/cka/)
