import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 20 }, // Фаза 1: наростання від 0 до 20 користувачів за 2 хвилини
    { duration: '5m', target: 20 }, // Фаза 2: стале навантаження 5 хвилин
    { duration: '2m', target: 0 },  // Фаза 3: спад до 0 за 2 хвилини
  ],
};

const BASE_URL = "http://cloud-lab-alb-1384162447.eu-central-1.elb.amazonaws.com";

export default function () {
  // 1 операція запису (POST /api/data) з JWT-токеном (якщо налаштовано автентифікацію)
  // Або без токена, якщо тестуєш публічний метод
  let payload = JSON.stringify({ text: `Test message from k6 user ${__VU}` });
  let params = {
    headers: {
      'Content-Type': 'application/json',
      // 'Authorization': 'Bearer ТВОЙ_ТОКЕН' // за потреби
    },
  };

  let postRes = http.post(`${BASE_URL}/api/data`, payload, params);
  check(postRes, { 'status is 201': (r) => r.status === 201 });

  // 8-10 операцій читання (GET /api/data)
  for (let i = 0; i < 9; i++) {
    let getRes = http.get(`${BASE_URL}/api/data`);
    check(getRes, { 'status is 200': (r) => r.status === 200 });
    sleep(1); // пауза між запитами
  }
}