# 6주차 Kubernetes 자동 확장 실습

이 저장소는 **요청을 받는 API와 대시보드**입니다. 별도 [week6_sender](https://github.com/Mok2Lee/week6_sender)는 Docker Compose로 요청을 보냅니다. 요청량을 바꾸고 Kubernetes가 API Pod 수를 조절하는 과정을 확인합니다.

## 실습 순서

1. 교수자가 제공한 **도구·이미지·Minikube 캐시**를 PC에 준비합니다.
2. 제공 이미지를 불러오고 **Minikube**를 시작합니다.
3. `k8s/`의 설정을 적용하고 **8080 대시보드**를 연결합니다.
4. 별도 발생기를 Compose로 실행하고 **8090 발생기**를 엽니다.
5. **40·120·220건/분**의 요청을 보내며 API Pod 수를 확인합니다.
6. HPA 목표를 **50 → 75건/분**으로 바꾸고 결과를 비교합니다.

**[학생 실습 안내](docs/student-lab.md)**의 순서와 명령을 따릅니다. 과제는 [요청량 관찰과 HPA 기준 변경](docs/assignment.md)입니다.

## 폴더와 터미널

| 폴더 | 내용 |
| --- | --- |
| `C:\lab\week6` | 이 저장소: API·대시보드·지표 앱·Kubernetes 설정 |
| `C:\lab\week6_sender` | 별도 요청 발생기 |
| `C:\lab\tools` | 제공된 `minikube.exe`, `kubectl.exe` |
| `C:\lab\offline` | 제공된 `week6_images.tar` |

두 프로젝트는 **나란히 둡니다**. 발생기를 `week6` 안으로 옮기지 않습니다.

| VS Code PowerShell | 작업 폴더 | 용도 |
| --- | --- | --- |
| **A — 실습 관리** | `C:\lab\week6` | Minikube·배포·Compose 실행·HPA 확인·정리 |
| **B — 대시보드 연결** | `C:\lab\week6` | `kubectl port-forward` 실행 상태 유지 |

터미널은 **2개**만 사용합니다. B는 대시보드를 연결하는 단계에서 만듭니다. Flask·Python은 이미지 안에 있으므로 Windows에 따로 설치하지 않습니다. 학생이 PowerShell 스크립트 파일이나 함수를 실행할 필요가 없습니다.

## 실행 화면

| 화면 | 주소 |
| --- | --- |
| Kubernetes 대시보드 | <http://localhost:8080> |
| Compose 요청 발생기 | <http://localhost:8090> |
| 프로젝트 검색·소개글 분량 검사 | <http://localhost:8080/projects.html> |

## 요청량과 HPA

HPA는 **Pod 1개당 평균 분당 50건**을 기준으로 API Pod 수를 조절합니다. 전체 최근 60초 요청 수를 50으로 나눈 뒤 올림하면 이론적인 목표 Pod 수입니다. 최소 1개, 최대 5개이며 **50건은 학습용 기준**입니다.

성공한 기능 API 요청(HTTP 2xx)만 집계합니다. health·대시보드 조회와 실패한 요청은 제외합니다. 최근 60초 집계와 Pod 준비에 시간이 걸리므로 결과가 즉시 바뀌지는 않습니다.

제공된 지표 앱이 요청량을 HPA에 전달합니다. 화면의 요청 수·응답 시간은 실제 측정값이며 CPU 사용률과 구분합니다. 지표 앱이 재시작하면 수업용 집계는 초기화됩니다.

## 학교와 집에서 같은 순서로 실행

수업 중 `docker build`나 패키지 설치를 하지 않고 **동일한 이미지 파일과 캐시**를 사용합니다. 학교의 SSL 인증서 문제로 다운로드가 막히는 상황을 줄이기 위한 구성입니다. 제공 파일 누락이나 PC 환경 차이까지 해결되는 것은 아니므로, 다운로드 오류가 나오면 [오류 확인](docs/student-lab.md#오류-확인)을 먼저 봅니다.

Pod 복구·업데이트·롤백은 [추가 실습](docs/student-lab.md#추가-실습)이며 과제 제출 항목이 아닙니다. [관리 기초](docs/management-basics.md)는 관련 개념을 정리한 참고 자료입니다.

기존 5주차 저장소를 덮어쓰지 않습니다. 강의 PPT·PDF, 배포용 이미지·캐시, 인증서·키·토큰은 이 저장소나 과제에 올리지 않습니다. 비공개 저장소의 학생 접근 권한은 교수자가 안내합니다.
