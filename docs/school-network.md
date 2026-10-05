# 학교 네트워크와 인증서

## 실패한 단계를 먼저 구분

|실패 단계|확인할 내용|
|---|---|
|Docker Desktop / Minikube 설치 파일|학교 제공 파일 또는 공식 HTTPS 다운로드, 브라우저 보안 경고 여부|
|`FROM python` / nginx pull|컨테이너 레지스트리 접근·Docker 프록시·신뢰 CA|
|Dockerfile의 pip install|PyPI 접근과 인증서 체인|
|Minikube start|노드 이미지와 Kubernetes 이미지 접근|
|Pod ErrImageNeverPull|태그와 Minikube image load, 네트워크 오류와 구분|

`--trusted-host`는 **pip가 해당 호스트에 접근하는 단계**에만 적용됩니다. Docker 이미지 pull이나 Minikube 시작 실패를 고치지 못합니다. 프록시 주소·인증정보를 저장소에 커밋하지 않습니다.

## 1. 기본 방식

기본 `api/Dockerfile`은 인증서를 검증합니다. 개인 네트워크와 인증서가 정상인 학교 환경에서는 그대로 사용합니다.

```powershell
docker build -t week6-api:v1 ./api
```

## 2. 정상 인증서를 사용하는 방식

학교 IT 담당자가 확인한 **공인 루트와 학교 CA를 포함하는 PEM 번들**을 `certs/ca-bundle.pem`에 둡니다. 출처가 불명확한 인증서는 설치하지 않습니다. 이 폴더는 `.gitignore`에 포함됩니다. BuildKit secret으로 빌드 중에만 파일을 제공합니다.

```powershell
docker build -f ./api/Dockerfile.ca --secret id=ca_bundle,src=./certs/ca-bundle.pem -t week6-api:v1 ./api
```

호스트의 OS·전역 pip 설정은 변경하지 않습니다. 이 방법은 pip 단계의 신뢰를 제공하며 레지스트리/Minikube 인증서 문제는 IT 담당자가 별도로 해결해야 합니다.

## 3. 학교 실습 한정 우회

교수자가 **학교의 TLS 인증서 문제임을 확인한 경우에만** 별도 Dockerfile을 선택합니다. `--trusted-host`는 지정한 호스트를 유효한 인증서가 없어도 신뢰하게 하므로 중간자 공격과 변조된 패키지 위험이 있습니다. 운영 이미지에 사용하지 않습니다. 인증서 문제가 해결되면 기본 방식으로 다시 빌드합니다.

```powershell
docker build -f ./api/Dockerfile.school -t week6-api:v1 ./api
docker build -f ./api/Dockerfile.school --build-arg APP_VERSION=v2 -t week6-api:v2 ./api
```

Dockerfile 안에도 학생이 볼 수 있도록 위험·사용 범위·정상 방식을 주석으로 적었습니다. 지난주 실제 수정 커밋인 [실습 3cc0ee7](https://github.com/Mok2Lee/week5_practice/commit/3cc0ee782cf7b26886781598ab6e471d62304e71), [과제 792d179](https://github.com/Mok2Lee/week5_workout/commit/792d1797ccfe12bc2d056606af54f50ec1e845c1)의 두 호스트를 사용합니다. 이번에는 `Flask==3.1.2`가 적힌 requirements.txt를 계속 읽습니다.

학교용 이미지 생성 후 Compose는 `docker compose up -d`로 시작합니다. `--build`를 붙이면 기본 Dockerfile로 다시 빌드하므로 인증서 오류가 재발할 수 있습니다. Minikube에는 선택한 방식으로 빌드한 이미지 태그를 `minikube image load ... -p week6`으로 전달합니다.

SSL 검증을 전역으로 끄거나 `git config --global http.sslVerify false`, pip 전역 trusted-host 저장, 브라우저 보안 경고 우회, 방화벽 전체 해제는 사용하지 않습니다.

참고: [pip trusted-host 옵션](https://pip.pypa.io/en/stable/cli/pip/#cmdoption-trusted-host), [pip HTTPS 인증서](https://pip.pypa.io/en/stable/topics/https-certificates/).
