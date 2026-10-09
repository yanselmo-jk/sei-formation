#!/bin/bash
# 큐 대기 프로브. 하는 일은 "노드에서 시작 시각을 남기고 60초 자는 것"뿐이다.
# 대기시간 = (노드가 기록한 시작 epoch) - (우리가 기록한 제출 epoch).
# common.sh가 이미 started.json 을 썼으므로 여기서는 자기만 하면 된다.
set -u
sleep 60
exit 0
