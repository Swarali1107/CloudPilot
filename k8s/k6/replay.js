import http from 'k6/http';

// rates.json = requests per SECOND, one number per trace-minute
const rates = JSON.parse(open('/scripts/rates.json'));
const STAGE = (__ENV.STAGE_SECONDS || '12') + 's';   // 1 trace-minute = 12 real seconds (5x replay)

export const options = {
  scenarios: {
    replay: {
      executor: 'ramping-arrival-rate',
      startRate: Math.max(1, Math.round(rates[0])),
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: rates.map(r => ({ target: Math.max(1, Math.round(r)), duration: STAGE })),
    },
  },
};

export default function () {
  http.get('http://demo-app/work', { timeout: '5s' });
}
