# 6주차 Kubernetes 실습

> 교수자 검토용 비공개 저장소입니다. 학생 Fork 안내는 공개 전환 또는 학생 접근 권한 설정 후 사용합니다.

지난주 Flask·nginx 앱의 **이미지 생성부터 다시 실행**하고, 같은 앱을 Kubernetes로 관리합니다. Windows Docker Desktop의 **Linux 컨테이너**와 VS Code의 **PowerShell**을 사용합니다. 기존 5주차 저장소는 그대로 둡니다.

## 학습 순서

1. Kubernetes 구성 요소와 원하는 상태를 이해합니다.
2. 새 저장소를 복제하고 이미지를 생성해 Compose로 기능을 확인합니다.
3. Minikube 클러스터를 실행하고 기본 명령을 확인합니다.
4. Deployment와 Service로 같은 앱을 실행합니다.
5. 복제본 확대, Pod 삭제 후 복구, 이미지 업데이트와 롤백을 확인합니다.
6. 관찰 결과를 기록하고 실습 자원을 정리합니다.

[학생용 상세 실습](docs/student-lab.md) 순서대로 진행합니다. [학교 네트워크·인증서 안내](docs/school-network.md)는 다운로드 오류가 있을 때 사용합니다. [추가 과제](docs/assignment.md)는 기본 실습 완료 후 진행합니다.

|구분|이번 주 기준|
|---|---|
|저장소 / 로컬 폴더|`week6_practice` / `week6`|
|이미지|`week6-api:v1`, `week6-web:v1`, 업데이트용 `week6-api:v2`|
|Compose 프로젝트|`week6`|
|Minikube 프로필 / 네임스페이스|`week6` / `week6`|
|Deployment / Service|`api`, `web`|
|포트|브라우저 8080, nginx 80, Flask 5000|

모든 상대 경로는 **복제한 week6 폴더**를 기준으로 합니다. 본인 작업 위치를 사용하며 특정 드라이브 경로를 요구하지 않습니다. PowerShell에서는 `curl.exe`를 사용하고, 명령은 한 줄씩 실행합니다. 실패한 명령 뒤에는 원인을 해결한 다음 진행합니다.

Minikube 시작 뒤 각 터미널에서 `function kubectl { minikube kubectl -p week6 -- @args }`를 실행하면 해당 클러스터와 맞는 kubectl을 사용합니다. 함수는 현재 터미널에서만 유지됩니다.

```text
api/                 지난주 Flask 검색·분량 검사 앱과 세 가지 Dockerfile
nginx/               지난주 화면, API 전달 대상은 api:5000
compose.yaml         이미지 생성과 기능 복습
k8s/                 Namespace, Deployment, Service
docs/                학생 실습, 학교 네트워크, 과제
tests/               앱 동작 검증
```

이 앱은 수업용 Flask 개발 서버를 사용합니다. 실제 운영 배포용 구성은 아닙니다. 지난주 과제의 SQLite 조회수 기능은 여러 Pod가 DB 파일을 공유해야 하는 별도 주제이므로 이번 기본 실습은 상태를 저장하지 않는 **지난주 실습 앱**을 사용합니다.

출처: [week5_practice](https://github.com/Mok2Lee/week5_practice/tree/3cc0ee782cf7b26886781598ab6e471d62304e71). 과제 저장소의 [SSL 수정](https://github.com/Mok2Lee/week5_workout/commit/792d1797ccfe12bc2d056606af54f50ec1e845c1)도 확인하여 학교용 빌드에 반영했습니다.

## 강의 자료

[강의 PPTX](materials/week6_Kubernetes_student_final.pptx) · [강의 PDF](materials/week6_Kubernetes_student_final.pdf) · [학생 실습 패키지 ZIP](materials/week6_student_package.zip)

검증: Windows Docker Desktop와 Minikube에서 이미지 생성, Compose, Kubernetes 배포, 3개 Pod 확장·복구, v2 업데이트·v1 롤백까지 실제 통과했습니다. 학교 네트워크·SSL 우회 빌드·학교 CA 빌드는 미실행입니다.
