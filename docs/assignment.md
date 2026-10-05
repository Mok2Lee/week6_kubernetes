# 6주차 추가 실습 및 과제

기본 실습에서 만든 **본인 week6_practice Fork**를 사용합니다. 지난주 저장소의 제출 내용을 덮어쓰지 않습니다. 제출기한과 제출 양식은 LMS 공지를 따릅니다.

1. `PROJECTS`에 가상의 프로젝트 한 개를 추가하고 v2 이미지를 생성합니다. 실제 학번·이름·비밀번호는 앱과 공개 저장소에 넣지 않습니다.
2. Kubernetes에 v2를 배포하고 웹 검색 결과에서 추가한 프로젝트를 확인합니다.
3. API Pod 3개 상태를 기록하고 하나를 삭제합니다. 새 이름의 Pod로 다시 3개가 된 결과를 기록합니다.
4. v1으로 롤백하여 프로젝트 추가 전 결과를 확인합니다. health의 version도 비교합니다.
5. 아래 표를 채우고 이번 주 자원을 정리합니다.

|확인 항목|기록할 내용|
|---|---|
|이미지|week6_01·week6_03 이미지 이름과 health의 version|
|배포|Deployment·Pod·Service 목록|
|동작|검색 결과, health의 version·pod|
|복구|삭제 전·후 Pod 이름과 최종 복제 수|
|롤백|버전과 검색 결과 변화|
|개념|Service selector가 필요한 이유, 수동 확장과 자동 복구의 차이|
|정리|api·web Deployment 삭제와 프로필 중지 결과|

스크린샷에는 관련 명령과 결과가 함께 보이게 합니다. 본인 원격 저장소 링크와 최종 커밋을 제출 문서에 적습니다. 학번·이름은 LMS 제출 파일명 등 교수자가 지정한 **비공개 제출 경로**에만 사용합니다. 지난주 최종본의 PDF 제출 방식을 이어가되, 세부 형식·마감은 이번 LMS 공지가 우선합니다.

```powershell
git status
git add api/app.py k8s/api.yaml
git commit -m "Complete week 6 Kubernetes practice"
git push
git rev-parse HEAD
```

인증서 파일, `.env`, Docker/클라우드 자격증명, 시험 정답, 다른 학생 정보는 커밋하지 않습니다.
