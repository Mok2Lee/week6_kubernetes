# 6주차 Kubernetes 자동 확장 실습

지난주 Flask·nginx 웹 프로젝트를 **요청을 보내는 앱과 요청을 받는 앱**으로 나눕니다. 요청 발생기는 Docker Compose로 실행하고, API 서버와 대시보드는 Kubernetes로 실행합니다.

> 교수자 검토용 비공개 저장소입니다. 학생 접근 권한은 교수자가 정합니다.

## 실습 목표

1. 요청 발생기의 슬라이더로 분당 요청량을 조절합니다.
2. Kubernetes 대시보드에서 실제 요청 수와 API Pod별 처리 결과를 봅니다.
3. HPA가 **Pod 1개당 분당 50건**을 기준으로 Pod 수를 바꾸는 과정을 확인합니다.
4. Pod 삭제 후 복구와 새 이미지 배포·롤백을 확인합니다.

HPA는 실제 Pod당 평균 요청량을 목표 50건과 비교합니다. 전체 최근 60초 요청 수를 50으로 나눈 뒤 올림하면 이론적인 목표 Pod 수가 됩니다. 최소 1개, 최대 5개입니다. **50건은 실습용 설정값**이며 Flask 서버의 실제 처리 한계를 뜻하지 않습니다. 요청량을 바꾸면 집계 시간과 HPA 확인 주기 때문에 결과가 바로 바뀌지 않습니다.

## 실행 환경과 파일

Windows Docker Desktop의 Linux 컨테이너, VS Code의 PowerShell, Minikube를 사용합니다. Flask는 이미지 안에 설치하므로 Windows에 별도로 설치하지 않습니다.

| 위치 | 역할 | 실행 환경 |
|---|---|---|
| `sender/` | 요청량 조절 화면과 요청 발생기 | Docker Compose |
| `api/` | 요청 처리와 Pod 이름·응답 시간 반환 | Kubernetes |
| `nginx/` | 대시보드 제공과 API 요청 전달 | Kubernetes |
| `metrics/` | 최근 60초 요청 수를 HPA에 전달 | Kubernetes |
| `k8s/` | Deployment·Service·HPA 등 설정 | Kubernetes |
| `scripts/` | 지표 연결 설정과 실습 정리 | PowerShell |

| 화면 | 주소 |
|---|---|
| Kubernetes 대시보드 | `http://localhost:8080` |
| Compose 요청 발생기 | `http://localhost:8090` |
| 지난주 검색·분량 검사 | `http://localhost:8080/projects.html` |

**[학생 실습 안내](docs/student-lab.md)** 순서대로 실행합니다. [관리 기초](docs/management-basics.md)와 [추가 과제](docs/assignment.md)는 기본 실습 뒤에 봅니다.

Dockerfile에는 지난주와 같은 학교용 pip trusted-host 옵션을 넣었습니다. Minikube 첫 실행의 노드 이미지 다운로드는 별도 준비가 필요합니다.

HPA는 Kubernetes의 실제 자동 확장 기능을 사용합니다. 요청량은 제공된 수업용 지표 앱이 전달합니다. 대시보드의 요청량과 응답 시간은 실제 측정값이며 CPU 사용률과 구분합니다. 지표 앱이 재시작하면 수업용 집계는 초기화됩니다.

요청량 지표에는 **성공적으로 처리한 기능 API 요청(HTTP 2xx)**을 포함합니다. health·대시보드 조회와 실패한 요청은 제외하며, 발생기의 실패 건수는 별도로 확인합니다.

기존 5주차 저장소를 덮어쓰지 않습니다. 강의 PPT·PDF와 교수자 정답은 저장소 밖에 보관합니다. `.lab/`의 생성된 인증서와 키는 커밋하지 않습니다.
