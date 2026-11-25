# Line Cost Copilot: LineOps + CostLedger

Vibe-a-thon (2nd Brain Labs x Geek Room), Track 3: a copilot that works across two systems.

**All data in this project is invented.** The loss rates are exaggerated for clarity. Nothing here has been validated with a real plant.

## What it does

A chip packaging line has three steps: bonding, moulding and final test. Cost builds up at each step, so a chip scrapped late has already paid for every earlier step. That means the machine with the lower loss rate is not always the cheaper one.

Two small FastAPI apps hold the facts. Synapse (Auto mode) turns each app into an MCP server. Claude Desktop calls both servers, takes loss counts from one and rupee prices from the other, and explains the result in plain language.

| Machine | Loss rate | Where chips are lost | Chips lost per batch | Rupee loss per batch |
|---|---|---|---|---|
| B1 | 8.0% | bonding (cheap) | 800 | Rs 40,000 |
| B2 | 7.0% | final test (expensive) | 700 | Rs 44,800 |

B2 has the lower loss rate but costs more in rupees. This is a known effect (late scrap costs more). The project does not claim a discovery. It shows the answer built from two systems, with its working visible.

## Architecture

```
Claude Desktop (agent + project instructions)
   |-- MCP server "lineops"      -> LineOps API    http://127.0.0.1:8001   production facts
   '-- MCP server "costledger"   -> CostLedger API http://127.0.0.1:8002   rupee pricing
```

Claude Desktop starts the `@2ndbrainlabs-ai/synapse-mcp` runner with `npx` for each server. There is no middleware. All maths lives in the two apps, and the agent only narrates. Every endpoint is a read-only GET.

## Endpoints

| App | Endpoint | Purpose |
|---|---|---|
| LineOps | `GET /machines/loss-profile` | Average chips lost per step for B1 and B2, usable batches only, excluded batches listed |
| LineOps | `GET /batches` | All 20 batches with losses per step and a usable/excluded status |
| LineOps | `GET /data-quality` | Batches with inconsistent records |
| LineOps | `GET /downtime-impact/{machine}` | Added live in the demo: excess chips lost after a stoppage (association, not proven cause) |
| CostLedger | `GET /step-costs` | Cost per step and the cost already spent on a chip if scrapped after each step |
| CostLedger | `GET /price-losses/{bonding}/{moulding}/{final_test}` | Turns loss counts into rupees |

Step names (`bonding`, `moulding`, `final_test`) are identical in both apps, so LineOps output can be passed straight into CostLedger.

## Questions that need both systems

1. **"Which machine, B1 or B2, costs us more in rupees per batch, and how does that compare with which one has the lower loss rate?"**
   LineOps gives the average losses, then CostLedger prices them. B2 costs more per batch, while B1 has the higher loss rate. Batch 447 is excluded, with the reason.
2. **"What did Tuesday's stoppage cost us?"** (the live update, below)
   LineOps gives the excess chips lost after the restart, then CostLedger prices them.

## Live update (shown in the recording)

1. Ask question 2. The agent says the tools cannot answer it, because no stoppage record exists.
2. Paste the `/downtime-impact/{machine}` block from `Lineops/downtime_snippet.txt` into `Lineops/main.py` and save.
3. Check `http://127.0.0.1:8001/downtime-impact/B2` in the browser: 6 stoppage hours, batches 455 and 457, 7 batches compared against, 900 extra chips lost at final test.
4. In `Lineops/`, run `synapse build --discover`. Synapse found 4 endpoints. Tick all four, because anything left unticked is removed.
5. Restart Claude Desktop (done in the recording) and ask question 2 again.
6. The agent now reports the 6-hour stoppage on B2, batches 455 and 457, 900 extra chips lost at final test, and Rs 57,600 from the CostLedger pricing tool. It states this is an association, not a proven cause, and that batch 447 is excluded.

The recording reuses the chat that held the earlier "cannot answer" reply, so the final answer opens by correcting it.

## Evidence

Hand checks (these match what the apps return):

- Carried cost: die Rs 40, then +10 bonding = Rs 50, +8 moulding = Rs 58, +6 final test = Rs 64.
- B1: 800 x Rs 50 = Rs 40,000 per batch.
- B2: 9 usable batches (7 at 600 lost, 2 at 1,050 lost) = 6,300 / 9 = 700 lost per batch. 700 x Rs 64 = Rs 44,800 per batch.
- Stoppage: (1,050 - 600) x 2 batches = 900 extra chips. 900 x Rs 64 = Rs 57,600.
- Batch 447 logs 120 final-test scraps but only 100 units reached final test, so it is flagged and excluded.

Reliability test: the main question was asked in 10 fresh chats, and all 10 were correct. Each run was scored against five points: both rupee figures right, batch 447 named as excluded, no money maths by the model, no advice and a note that the data is invented, and the pricing requests visible in the CostLedger terminal. The test used one fixed question and was scored by the author. The tally is in `reliability_tally.txt`.

## Agent rules (project instructions in Claude Desktop)

```
You are a read-only explainer for a chip packaging line (bonding, moulding, final test). All data is invented, so say so in every answer.

- Explain each chip term in one plain sentence the first time you use it.
- For cost questions, get chip losses from the lineops tools, then price them with the costledger price-losses tool. Never calculate rupee amounts yourself: no multiplying, adding, subtracting, percentages or averages of money. You may say which of two tool-returned figures is larger, and show both.
- Label every number as measured (from the tools), estimated, or excluded. Name any excluded batch and the reason.
- Describe and report only. Never recommend actions. Never say an association is a cause.
- Don't guess beyond what the tools return. If the tools can't answer, say what is missing.
```

## Run it yourself

Needs Python 3.9+ (built on 3.13), Node.js 22, the Synapse CLI (built with 0.1.9), a Synapse API key and Claude Desktop.

```
pip install fastapi uvicorn
npm install -g @2ndbrainlabs-ai/synapse-cli
```

1. Start each app in its own terminal:
   ```
   cd costledger && python -m uvicorn main:app --port 8002 --reload
   cd Lineops    && python -m uvicorn main:app --port 8001 --reload
   ```
2. In each app folder, run `synapse init`, then `synapse build --auto --all-endpoints`. When asked where the API is deployed, enter `http://127.0.0.1:8002` for CostLedger and `http://127.0.0.1:8001` for LineOps.
3. Add both servers to Claude Desktop (Settings > Developer > Edit Config). Use your own key, and never commit this file:
   ```json
   {
     "mcpServers": {
       "costledger": {
         "command": "npx",
         "args": ["-y", "@2ndbrainlabs-ai/synapse-mcp"],
         "env": {
           "SYNAPSE_SERVER_ID": "50d06b64-6ce5-4419-9d14-8dffeef5727b",
           "SYNAPSE_API_KEY": "<your key>",
           "ENDPOINT_BASE_URL": "http://127.0.0.1:8002"
         }
       },
       "lineops": {
         "command": "npx",
         "args": ["-y", "@2ndbrainlabs-ai/synapse-mcp"],
         "env": {
           "SYNAPSE_SERVER_ID": "5202843a-a094-4c39-99b7-8596f832cbfe",
           "SYNAPSE_API_KEY": "<your key>",
           "ENDPOINT_BASE_URL": "http://127.0.0.1:8001"
         }
       }
     }
   }
   ```
   The server IDs above belong to our Synapse account. Building your own copy gives you your own IDs.
4. Fully restart Claude Desktop, put the agent rules in a project's instructions, and ask the questions above.

## What we observed about Synapse Auto mode (Windows, CLI 0.1.9)

- Apps running on the local machine work. The runner calls the address in `ENDPOINT_BASE_URL`, so no deployment was needed.
- Path parameters (`/price-losses/{bonding}/{moulding}/{final_test}`) became tool inputs, shown as strings. FastAPI converts them to numbers. Query parameters (`?name=...`) did not appear as tool inputs in our test, so the endpoints use path parameters.
- Docstrings became the tool descriptions, so they are written for the agent.
- `synapse build --discover` kept the same server ID, so the Claude Desktop config did not change. Endpoints left unticked in the menu were removed.
- On Windows, installing the CLI failed on Node 26 (a parser dependency tried to compile and needed Visual Studio's C++ tools). Node 22 installed it without problems.

## Limits

- Invented data only. Not validated with any real plant, and not a replacement for yield or MES systems.
- Read-only. The agent explains and reports. It does not recommend actions, and it does not present an association as a cause.
- The stoppage figure covers only the value of the extra scrapped chips. The apps hold no cost for the 6 idle hours.
- The agent is Claude Desktop connected to both MCP servers. This was our design choice, and we did not build separate agent code.
- The live update was recorded once. We did not time `synapse build --discover`, and we did not test whether Claude Desktop needs a restart to see a new tool.
- The reliability result is one question, one model (Sonnet 5.5, as shown in the recording), scored by the author.
- Chip-term explanations come from the model's general knowledge, not from the apps.
- The servers only work while both apps are running locally.

## Files

```
costledger/main.py            CostLedger app
Lineops/main.py               LineOps app (includes the endpoint added in the live demo)
Lineops/downtime_snippet.txt  the endpoint block pasted live
reliability_tally.txt         10-run tally
ViBEATHON_FINAL_.mp4          demo recording
```
