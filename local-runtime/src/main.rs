use rusqlite::{params, Connection};
use serde_json::{json, Value};
use std::{
    env, fs,
    path::{Path, PathBuf},
};
fn id(v: &Value, k: &str) -> Result<String, String> {
    let s = v[k].as_str().ok_or(format!("missing {k}"))?;
    if s.is_empty()
        || !s
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"_-".contains(&c))
    {
        return Err(format!("invalid {k}"));
    }
    Ok(s.into())
}
fn save(p: &Path, v: &Value) -> Result<(), String> {
    fs::create_dir_all(p.parent().unwrap()).map_err(|e| e.to_string())?;
    let tmp = p.with_extension("tmp");
    fs::write(&tmp, serde_json::to_vec_pretty(v).unwrap()).map_err(|e| e.to_string())?;
    fs::rename(tmp, p).map_err(|e| e.to_string())
}
fn read(p: &Path) -> Result<Value, String> {
    serde_json::from_slice(&fs::read(p).map_err(|e| e.to_string())?).map_err(|e| e.to_string())
}
fn dispatch(root: &Path, db: &Connection, v: Value) -> Result<Value, String> {
    let op = v["op"].as_str().unwrap_or("");
    if op == "list" {
        let mut q = db
            .prepare("SELECT id, data FROM projects ORDER BY id")
            .map_err(|e| e.to_string())?;
        let a = q
            .query_map([], |r| r.get::<_, String>(1))
            .map_err(|e| e.to_string())?
            .map(|x| serde_json::from_str::<Value>(&x.unwrap()).unwrap())
            .collect::<Vec<_>>();
        return Ok(json!(a));
    }
    let project = id(&v, "project")?;
    let base = root.join("projects").join(&project);
    if op == "register" {
        let repo = fs::canonicalize(v["repo"].as_str().ok_or("missing repo")?)
            .map_err(|e| e.to_string())?;
        if !repo.join(".git").exists() {
            return Err("repo must be a local Git checkout".into());
        }
        if base.exists() {
            return Err("project already exists".into());
        }
        let data =
            json!({"id":project,"repo":repo,"name":v["name"],"replay_status":"unconfigured"});
        save(&base.join("project.json"), &data)?;
        for d in ["blueprint", "tooling", "datasets", "sprints"] {
            fs::create_dir_all(base.join(d)).map_err(|e| e.to_string())?;
        }
        db.execute(
            "INSERT INTO projects VALUES (?1,?2)",
            params![project, data.to_string()],
        )
        .map_err(|e| e.to_string())?;
        return Ok(data);
    }
    if !base.join("project.json").exists() {
        return Err("unknown project".into());
    }
    if op == "workspace" {
        let info = dispatch(root, db, json!({"op":"inspect","project":project}))?;
        let mut contents = serde_json::Map::new();
        let mut errors = Vec::new();
        let mut total = 0usize;
        for file in info["files"].as_array().ok_or("invalid file index")? {
            let path = file["path"].as_str().ok_or("invalid file path")?;
            if !["blueprint/", "tooling/", "datasets/", "sprints/"]
                .iter()
                .any(|p| path.starts_with(p))
            {
                continue;
            }
            if ![
                "json", "md", "py", "mjs", "js", "yaml", "yml", "txt", "patch",
            ]
            .iter()
            .any(|e| path.ends_with(&format!(".{e}")))
            {
                continue;
            }
            if total + file["bytes"].as_u64().unwrap_or(0) as usize > 32_000_000 {
                errors.push(format!("{path}: workspace preview exceeds 32MB"));
                continue;
            }
            match dispatch(root, db, json!({"op":"read","project":project,"path":path})) {
                Ok(result) => {
                    total += result["content"].as_str().unwrap_or("").len();
                    contents.insert(path.into(), result["content"].clone());
                }
                Err(error) => errors.push(format!("{path}: {error}")),
            }
        }
        return Ok(
            json!({"project":info["project"],"files":info["files"],"contents":contents,"errors":errors}),
        );
    }
    if op == "inspect" {
        let mut files = vec![];
        fn walk(p: &Path, b: &Path, a: &mut Vec<Value>) {
            if let Ok(xs) = fs::read_dir(p) {
                for x in xs.flatten() {
                    let p = x.path();
                    if p.is_symlink() {
                        continue;
                    }
                    if p.is_dir() {
                        walk(&p, b, a)
                    } else {
                        a.push(json!({"path":p.strip_prefix(b).unwrap().to_string_lossy(),"bytes":x.metadata().map(|m|m.len()).unwrap_or(0)}));
                    }
                }
            }
        }
        walk(&base, &base, &mut files);
        return Ok(json!({"project":read(&base.join("project.json"))?,"files":files}));
    }
    if op == "read" {
        let rel = v["path"].as_str().ok_or("missing path")?;
        let p = fs::canonicalize(base.join(rel)).map_err(|e| e.to_string())?;
        let canonical = fs::canonicalize(&base).map_err(|e| e.to_string())?;
        if !p.starts_with(canonical) {
            return Err("path outside project".into());
        }
        if fs::metadata(&p).map_err(|e| e.to_string())?.len() > 4_000_000 {
            return Err("file too large".into());
        }
        return Ok(json!({"content":fs::read_to_string(p).map_err(|e|e.to_string())?}));
    }
    if op == "import" {
        let dataset = id(&v, "dataset")?;
        let version = id(&v, "version")?;
        let dst = base.join("datasets").join(dataset).join(version);
        if dst.exists() {
            return Err("dataset version is immutable".into());
        }
        let records = v["records"].as_array().ok_or("records must be array")?;
        if records.is_empty() {
            return Err("empty dataset".into());
        }
        let mut seen = std::collections::HashSet::new();
        for rec in records {
            let c = id(rec, "case_id")?;
            id(rec, "record_id")?;
            if !seen.insert(c) {
                return Err("duplicate case_id".into());
            }
            for k in ["task_input", "trajectory", "annotation", "reflection"] {
                if rec.get(k).is_none() || rec[k].is_null() {
                    return Err(format!("missing {k}"));
                }
            }
            if !rec["trajectory"].is_array()
                || !rec["annotation"].is_object()
                || !rec["reflection"].is_string()
            {
                return Err("invalid record types".into());
            }
        }
        let staging = dst.with_extension("staging");
        if staging.exists() {
            fs::remove_dir_all(&staging).map_err(|e| e.to_string())?
        }
        for rec in records {
            save(
                &staging
                    .join("cases")
                    .join(id(rec, "case_id")?)
                    .join("record.json"),
                rec,
            )?;
        }
        save(
            &staging.join("manifest.json"),
            &json!({"count":records.len(),"schema_version":1}),
        )?;
        fs::rename(staging, &dst).map_err(|e| e.to_string())?;
        return Ok(json!({"path":dst,"count":records.len()}));
    }
    if op == "create-sprint" {
        let sprint = id(&v, "sprint")?;
        let dataset = id(&v, "dataset")?;
        let version = id(&v, "version")?;
        let src = base.join("datasets").join(dataset).join(version);
        read(&src.join("manifest.json"))?;
        let dst = base.join("sprints").join(sprint);
        if dst.exists() {
            return Err("sprint already exists".into());
        }
        fn copy(a: &Path, b: &Path) -> Result<(), String> {
            fs::create_dir_all(b).map_err(|e| e.to_string())?;
            for e in fs::read_dir(a).map_err(|e| e.to_string())? {
                let e = e.map_err(|e| e.to_string())?;
                if e.path().is_symlink() {
                    return Err("symlink not allowed in snapshot".into());
                }
                if e.path().is_dir() {
                    copy(&e.path(), &b.join(e.file_name()))?
                } else {
                    fs::copy(e.path(), b.join(e.file_name())).map_err(|e| e.to_string())?;
                }
            }
            Ok(())
        }
        copy(&src, &dst.join("rounds/000"))?;
        copy(&base.join("blueprint"), &dst.join("snapshots/blueprint"))?;
        save(
            &dst.join("sprint.json"),
            &json!({"dataset":v["dataset"],"version":v["version"],"baseline":"historical","source":v["source"],"budget":v["budget"]}),
        )?;
        return Ok(json!({"path":dst}));
    }
    Err(format!("unsupported operation {op}"))
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1)
    }
}
fn run() -> Result<(), String> {
    let a: Vec<String> = env::args().collect();
    let root = PathBuf::from(env::var("RSI_DATA_DIR").unwrap_or(".data".into()));
    fs::create_dir_all(&root).map_err(|e| e.to_string())?;
    let db = Connection::open(root.join("rsi.sqlite")).map_err(|e| e.to_string())?;
    db.execute_batch("PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,data TEXT NOT NULL);").map_err(|e|e.to_string())?;
    if a.get(1).map(String::as_str) == Some("dispatch") {
        let input = fs::read_to_string(a.get(2).ok_or("dispatch requires request.json")?)
            .map_err(|e| e.to_string())?;
        let out = dispatch(
            &root,
            &db,
            serde_json::from_str(&input).map_err(|e| e.to_string())?,
        )?;
        println!("{}", out);
        return Ok(());
    }
    if a.get(1).map(String::as_str) != Some("serve") {
        return Err("usage: rsi-runtime dispatch request.json | serve".into());
    }
    let server = tiny_http::Server::http(format!(
        "127.0.0.1:{}",
        env::var("RSI_PORT").unwrap_or("0".into())
    ))
    .map_err(|e| e.to_string())?;
    let addr = server.server_addr().to_string();
    let discovery = root.join("runtime.json");
    save(
        &discovery,
        &json!({"url":format!("http://{addr}"),"pid":std::process::id(),"protocol":1}),
    )?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&discovery, fs::Permissions::from_mode(0o600))
            .map_err(|e| e.to_string())?;
    }
    println!("http://{addr}");
    for mut req in server.incoming_requests() {
        // Loopback-only UI: reject DNS rebinding and cross-site browser requests.
        let host = req
            .headers()
            .iter()
            .find(|h| h.field.equiv("Host"))
            .map(|h| h.value.as_str());
        if host != Some(addr.as_str()) {
            let _ = req.respond(
                tiny_http::Response::from_string(json!({"error":"host denied"}).to_string())
                    .with_status_code(403),
            );
            continue;
        }
        let origin = req
            .headers()
            .iter()
            .find(|h| h.field.equiv("Origin"))
            .map(|h| h.value.as_str());
        if origin.is_some_and(|o| o != format!("http://{addr}")) {
            let _ = req
                .respond(tiny_http::Response::from_string("origin denied").with_status_code(403));
            continue;
        }
        let (body, mime, code) = if req.url() == "/" && req.method() == &tiny_http::Method::Get {
            (
                include_str!("../web/index.html").to_string(),
                "text/html",
                200,
            )
        } else if req.url() == "/health" {
            ("{\"protocol\":1}".into(), "application/json", 200)
        } else if req.url() == "/api" && req.method() == &tiny_http::Method::Post {
            let mut s = String::new();
            use std::io::Read;
            let out = req
                .as_reader()
                .take(8_000_001)
                .read_to_string(&mut s)
                .map_err(|e| e.to_string())
                .and_then(|_| {
                    if s.len() > 8_000_000 {
                        Err("request too large".into())
                    } else {
                        serde_json::from_str(&s).map_err(|e| e.to_string())
                    }
                })
                .and_then(|v| dispatch(&root, &db, v));
            match out {
                Ok(v) => (v.to_string(), "application/json", 200),
                Err(e) => (json!({"error":e}).to_string(), "application/json", 400),
            }
        } else {
            ("not found".into(), "text/plain", 404)
        };
        let _ = req.respond(
            tiny_http::Response::from_string(body)
                .with_status_code(code)
                .with_header(tiny_http::Header::from_bytes("Content-Type", mime).unwrap())
                .with_header(tiny_http::Header::from_bytes("Cache-Control", "no-store").unwrap()),
        );
    }
    Ok(())
}
