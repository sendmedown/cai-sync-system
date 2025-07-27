curl -Method Post http://localhost:10000/nugget/create `
  -Headers @{ "Content-Type" = "application/json"; "Authorization" = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJSaWNoYXJkIiwiaWF0IjoxNzUzNjQ0Nzc5LCJleHAiOjE3NTM2NDgzNzl9.83zReA462VxEwLPw_njfEuryuu9XffnvHoiu2lrMZgU" } `
  -Body '{'userId': 'Richard', 'content': 'Testing Nugget', 'promptId': 'prompt-abc123', 'context': {'sessionId': 'test123'}}'
