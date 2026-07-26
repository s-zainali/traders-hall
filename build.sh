#!/usr/bin/env bash
set -e
cd traders-hall-frontend
npm install
npm run build
cd ../traders-hall-backend
pip install -r "requirements.txt"
alembic upgrade head
