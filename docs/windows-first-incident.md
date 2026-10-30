# Your first support investigation on Windows

This exercise uses a small local Python service and invented customer data. It does not require Docker, VirtualBox, AWS or a database. It gives you a safe place to practise investigating an API authentication failure.

Do one stage at a time. If a command behaves differently from the description, stop and record the exact message before changing your computer's settings. This guide has not been tested on your laptop.

## 1. Check Python

Open Windows PowerShell and run:

```powershell
py --version
```

Python 3.11 or later is needed. If `py` is not recognized, try `python --version` instead. If neither command works, pause here and investigate Python installation; do not continue with the later commands. Use whichever command works (`py` or `python`) in the next stage. An app-execution alias can appear installed without a working interpreter, so the version output matters.

## 2. Get the project

On the [repository page](https://github.com/kinz0042/cloud-support-engineering-lab), choose **Code**, then **Download ZIP**. In Windows File Explorer, extract the downloaded ZIP. Open the extracted folder that contains `README.md`, `app`, and `incidents`.

This ZIP is a snapshot of the files. It does not contain the Git history or automatically update when the repository changes; the Git workflow comes later.

## 3. Start the local service

In File Explorer's address bar while viewing that project folder, type `powershell` and press Enter. In the PowerShell window that opens, run:

```powershell
py app/server.py
```

If the working command in stage 1 was `python`, use `python app/server.py` instead. You should see `Local lab listening at http://127.0.0.1:8080`. Leave this window open. If the command reports the port is already in use, record the error; do not terminate an unfamiliar process.

## 4. Investigate the complaint

The synthetic customer says: “Our order integration stopped syncing. The health page still says OK. Please investigate without changing our order data.”

Open a **second** PowerShell window and run the two commands one at a time:

```powershell
curl.exe -i http://127.0.0.1:8080/health
```

```powershell
curl.exe -i http://127.0.0.1:8080/v1/orders -H "Authorization: lab-demo-token-not-a-secret"
```

If `curl.exe` is unavailable, stop and investigate the exact error. Do not substitute PowerShell's `curl` alias: it can behave differently.

Record what you actually see: each HTTP status, response body, `X-Request-ID` and the time. The synthetic token is public, but never copy real credentials into notes or screenshots. The request IDs should match entries in the first window's server log.

Before changing the request, write two possible explanations. What does the health result establish? What does it not establish? Compare the failed request with the `WWW-Authenticate` response header and the [API service documentation](../README.md#run-locally). Test your leading hypothesis, then make a second request with no credentials as a negative control. Record your actual observations rather than relying on an expected answer.

Use the [incident brief](../incidents/INC-001/brief.md) and [record template](../incidents/TEMPLATE.md) to write an initial customer response, the evidence, your hypotheses, the correction and its validation. Mark any help you received. This is an assisted learning exercise until you can solve an unfamiliar incident independently.

When finished, click the first PowerShell window and press **Ctrl+C** to stop the service. No database or persistent customer data is created by this exercise.

## Scope of verification

On 30 October 2026, [this Windows CI run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41020216594) started the foundation service and used Windows PowerShell and `curl.exe` to verify health 200, malformed credential 401, corrected credential 200, missing credential 401, and request IDs. It ran on a hosted Windows Server 2025 runner at commit `af96a74a600f3c46e27d15bb62f60272351e71a0`. It did not test the ZIP download, interactive setup or the learner's laptop. A hosted runner cannot prove compatibility on your computer.
