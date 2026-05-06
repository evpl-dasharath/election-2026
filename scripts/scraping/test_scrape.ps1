Invoke-WebRequest -Uri "http://localhost:8001/api/scraper/run/" -Method POST -ContentType "application/json" -Body '{"ac_number":1,"test_mode":true}' | Select-Object -ExpandProperty Content
