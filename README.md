# 6주차 Kubernetes 자동 확장 실습

이 저장소는 **요청을 받는 API와 대시보드**입니다. 별도 [week6_practice](https://github.com/Mok2Lee/week6_practice)는 Docker Compose로 요청을 보냅니다. 요청량을 바꾸고 **Kubernetes가 API Pod 수를 조절하는 과정**을 확인합니다.

## 프로젝트와 터미널

두 프로젝트를 C: 바로 아래에 둡니다. VS Code PowerShell은 **프로젝트별로 하나씩** 사용합니다.

| 터미널 | 프로젝트 위치 | 실행 내용 |
| --- | --- | --- |
| **A — 요청 발생기** | `C:\week6_practice` | `docker compose up` |
| **B — Kubernetes** | `C:\week6_kubernetes` | 이미지 빌드·배포·상태 확인 |

A는 발생기 로그를 표시한 채 두고, Kubernetes 명령은 B에서 실행합니다.

## 실습 순서

1. **A:** `docker compose up`으로 요청 발생기를 실행합니다.
2. **B:** Minikube를 시작하고 API·웹·지표 이미지를 직접 빌드합니다.
3. **B:** 이미지를 Minikube에 전달하고 `k8s/`의 YAML을 배포합니다.
4. **브라우저:** 발생기에서 40 → 120 → 220건/분을 보내고 Pod 수를 확인합니다.
5. **B:** HPA 목표를 50 → 75건/분으로 바꾸고 결과를 비교합니다.

명령과 결과 확인은 **[학생 실습 안내](docs/student-lab.md)**, 제출 내용은 **[과제 안내](docs/assignment.md)**를 따릅니다.

| 화면 | 주소 |
| --- | --- |
| Compose 요청 발생기 | <http://localhost:8090> |
| Kubernetes 대시보드 | <http://localhost:8080> |
| 프로젝트 검색·소개글 분량 검사 | <http://localhost:8080/projects.html> |

## 요청량과 HPA

HPA는 **Pod 1개당 평균 분당 50건**을 기준으로 API Pod 수를 조절합니다. 이론적 목표는 **전체 최근 60초 요청 수 ÷ 50을 올림**한 값이며, 최소 1개·최대 5개입니다. 50건은 이번 수업의 학습용 기준입니다.

성공한 기능 API 요청만 집계하며 health·대시보드 조회·실패 요청은 제외합니다. 요청 수 집계와 새 Pod 준비에는 시간이 걸립니다. 제공된 지표 앱은 요청 수를 HPA에 전달하며, **요청 수는 CPU 사용률과 다른 값**입니다.

Pod 복구·업데이트·롤백은 [추가 실습](docs/student-lab.md#추가-실습), 관련 개념은 [관리 기초](docs/management-basics.md)를 참고합니다.
