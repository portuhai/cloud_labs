import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },
    { duration: '6m', target: 100 },
    { duration: '2m', target: 0 },
  ],
};

const BASE_URL = "http://cloud-lab-alb-1384162447.eu-central-1.elb.amazonaws.com";

export default function () {
  let payload = JSON.stringify({ text: `Test message from k6 user ${__VU}` });
  let params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  let postRes = http.post(`${BASE_URL}/api/data`, payload, params);
  check(postRes, { 'status is 201': (r) => r.status === 201 });

  for (let i = 0; i < 9; i++) {
    let getRes = http.get(`${BASE_URL}/api/data`);
    check(getRes, { 'status is 200': (r) => r.status === 200 });
    sleep(0.01);
  }
}