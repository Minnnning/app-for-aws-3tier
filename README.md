백엔드 (FastAPI):

main.py의 DATABASE_URL을 직접 코드에 넣는 대신, EC2 인스턴스의 환경 변수로 설정해야 합니다. 값은 AWS RDS 생성 후 얻게 되는 엔드포인트 주소를 사용합니다.

예: postgresql://<RDS_USER>:<RDS_PASSWORD>@<RDS_ENDPOINT_URL>/<DB_NAME>

백엔드 유저데이터
#!/bin/bash
# su - ec2-user -c "..." 명령을 사용해 ec2-user 권한으로 스크립트를 실행
su - ec2-user -c "cd /home/ec2-user/backend && nohup /home/ec2-user/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &"