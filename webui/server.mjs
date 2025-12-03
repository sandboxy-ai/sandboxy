import express from "express";
import { spawn } from "child_process";
import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// Configuration
const MODULES_DIR = path.join(__dirname, "..", "modules");
const RUNS_DIR = path.join(__dirname, "..", "runs");
const PORT = process.env.PORT || 3000;

/**
 * GET /api/modules - List available MDL modules
 */
app.get("/api/modules", async (req, res) => {
  try {
    await fs.mkdir(MODULES_DIR, { recursive: true });
    const files = await fs.readdir(MODULES_DIR);
    const ymls = files.filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"));

    const modules = await Promise.all(
      ymls.map(async (f) => {
        const fullPath = path.join(MODULES_DIR, f);
        const content = await fs.readFile(fullPath, "utf8");
        // Extract id and description from YAML (simple regex)
        const idMatch = content.match(/^id:\s*["']?(.+?)["']?\s*$/m);
        const descMatch = content.match(/^description:\s*["']?(.+?)["']?\s*$/m);
        return {
          filename: f,
          path: fullPath,
          id: idMatch ? idMatch[1] : f,
          description: descMatch ? descMatch[1] : "",
        };
      })
    );

    res.json({ modules, count: modules.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/agents - List available agents
 */
app.get("/api/agents", async (req, res) => {
  try {
    const agentsDir = path.join(__dirname, "..", "agents", "core");
    await fs.mkdir(agentsDir, { recursive: true });
    const files = await fs.readdir(agentsDir);
    const ymls = files.filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"));

    const agents = await Promise.all(
      ymls.map(async (f) => {
        const fullPath = path.join(agentsDir, f);
        const content = await fs.readFile(fullPath, "utf8");
        const idMatch = content.match(/^id:\s*["']?(.+?)["']?\s*$/m);
        const nameMatch = content.match(/^name:\s*["']?(.+?)["']?\s*$/m);
        const modelMatch = content.match(/^model:\s*["']?(.+?)["']?\s*$/m);
        return {
          filename: f,
          id: idMatch ? idMatch[1] : f,
          name: nameMatch ? nameMatch[1] : f,
          model: modelMatch ? modelMatch[1] : "unknown",
        };
      })
    );

    res.json({ agents, count: agents.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/run - Run a module with an agent
 * Body: { moduleFile: string, agentId?: string }
 */
app.post("/api/run", async (req, res) => {
  const { moduleFile, agentId } = req.body;

  if (!moduleFile) {
    return res.status(400).json({ error: "moduleFile is required" });
  }

  const runId = `${Date.now()}`;
  const outPath = path.join(RUNS_DIR, `run_${runId}.json`);

  try {
    await fs.mkdir(RUNS_DIR, { recursive: true });

    // Build command arguments
    const args = ["run", moduleFile, "-o", outPath];
    if (agentId) {
      args.push("--agent-id", agentId);
    }

    // Spawn sandboxy CLI
    const proc = spawn("sandboxy", args, {
      cwd: path.join(__dirname, ".."),
      env: { ...process.env },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", async (code) => {
      if (code !== 0) {
        return res.status(500).json({
          error: `sandboxy exited with code ${code}`,
          stderr,
          stdout,
        });
      }

      try {
        const content = await fs.readFile(outPath, "utf8");
        res.json({
          runId,
          result: JSON.parse(content),
        });
      } catch (err) {
        res.status(500).json({
          error: "Failed to read result file",
          details: err.message,
        });
      }
    });

    proc.on("error", (err) => {
      res.status(500).json({
        error: "Failed to spawn sandboxy",
        details: err.message,
      });
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/runs - List all runs
 */
app.get("/api/runs", async (req, res) => {
  try {
    await fs.mkdir(RUNS_DIR, { recursive: true });
    const files = await fs.readdir(RUNS_DIR);
    const runs = files
      .filter((f) => f.startsWith("run_") && f.endsWith(".json"))
      .map((f) => {
        const match = f.match(/run_(\d+)\.json/);
        return {
          id: match ? match[1] : f,
          filename: f,
          path: path.join(RUNS_DIR, f),
        };
      })
      .sort((a, b) => b.id.localeCompare(a.id)); // Sort newest first

    res.json({ runs, count: runs.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/runs/:id - Get a specific run result
 */
app.get("/api/runs/:id", async (req, res) => {
  const runPath = path.join(RUNS_DIR, `run_${req.params.id}.json`);

  try {
    const content = await fs.readFile(runPath, "utf8");
    res.json(JSON.parse(content));
  } catch (error) {
    if (error.code === "ENOENT") {
      return res.status(404).json({ error: "Run not found" });
    }
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/validate - Validate a module
 * Body: { moduleFile: string }
 */
app.post("/api/validate", async (req, res) => {
  const { moduleFile } = req.body;

  if (!moduleFile) {
    return res.status(400).json({ error: "moduleFile is required" });
  }

  const proc = spawn("sandboxy", ["validate", moduleFile], {
    cwd: path.join(__dirname, ".."),
  });

  let stdout = "";
  let stderr = "";

  proc.stdout.on("data", (data) => {
    stdout += data.toString();
  });

  proc.stderr.on("data", (data) => {
    stderr += data.toString();
  });

  proc.on("close", (code) => {
    res.json({
      valid: code === 0,
      message: code === 0 ? stdout.trim() : stderr.trim(),
    });
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Sandboxy WebUI listening on http://localhost:${PORT}`);
});
