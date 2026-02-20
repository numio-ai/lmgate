// stats.js — Response body accumulation + stats JSONL writing.
// Uses js_body_filter to accumulate response body chunks.
// On last chunk, builds a stats entry and appends it to the JSONL file.
//
// Note: ngx.fetch() is async and NOT supported in js_body_filter.
// We use synchronous fs.appendFileSync() instead.

var fs = require("fs");

var body_buffer = "";
var MAX_BODY_SIZE = 2 * 1024 * 1024; // 2 MB cap
var truncated = false;

var STATS_PATH = "/data/stats.jsonl";

var HOST_TO_PROVIDER = {
    "api.openai.com": "openai",
    "api.anthropic.com": "anthropic",
    "aiplatform.googleapis.com": "google"
};

function detect_provider(host) {
    return HOST_TO_PROVIDER[host] || "unknown";
}

function parse_json(body) {
    if (!body) return null;
    try {
        return JSON.parse(body);
    } catch (e) {
        // Try SSE: find last data: {...} line
        var last = null;
        var lines = body.split("\n");
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (line.indexOf("data: ") === 0 && line !== "data: [DONE]") {
                try { last = JSON.parse(line.substring(6)); } catch (e2) {}
            }
        }
        return last;
    }
}

function extract_tokens(provider, parsed) {
    if (!parsed) return [null, null];
    try {
        if (provider === "openai") {
            var u = parsed.usage;
            return u ? [u.prompt_tokens || null, u.completion_tokens || null] : [null, null];
        }
        if (provider === "anthropic") {
            var u = parsed.usage;
            return u ? [u.input_tokens || null, u.output_tokens || null] : [null, null];
        }
        if (provider === "google") {
            var m = parsed.usageMetadata;
            return m ? [m.promptTokenCount || null, m.candidatesTokenCount || null] : [null, null];
        }
    } catch (e) {}
    return [null, null];
}

function mask_key(raw) {
    if (!raw) return "";
    return raw.slice(-6);
}

function extract_raw_key(auth_header, x_api_key) {
    if (auth_header) {
        if (auth_header.toLowerCase().indexOf("bearer ") === 0) {
            return auth_header.substring(7).trim();
        }
        return auth_header;
    }
    return x_api_key || "";
}

function accumulate(r, data, flags) {
    // Skip stats for non-proxied responses (e.g. 403 from auth_request).
    // The body filter fires for ALL responses including nginx error pages.
    if (r.status === 403 || r.status === 401) {
        r.sendBuffer(data, flags);
        return;
    }

    if (!truncated && body_buffer.length + data.length <= MAX_BODY_SIZE) {
        body_buffer += data;
    } else {
        truncated = true;
    }

    if (flags.last) {
        try {
            var host = r.variables.upstream_host || "";
            var provider = detect_provider(host);
            var response_body = truncated ? "" : body_buffer;
            var parsed = parse_json(response_body);
            var tokens = extract_tokens(provider, parsed);
            var auth_header = r.headersIn["Authorization"] || "";
            var x_api_key = r.headersIn["X-Api-Key"] || "";
            var raw_key = extract_raw_key(auth_header, x_api_key);

            var entry = JSON.stringify({
                timestamp: new Date().toISOString(),
                lmgate_id: r.variables.lmgate_id || "",
                provider: provider,
                endpoint: r.variables.request_uri,
                model: parsed ? (parsed.model || null) : null,
                status: r.status,
                input_tokens: tokens[0],
                output_tokens: tokens[1],
                masked_key: mask_key(raw_key),
                error_type: null
            });

            fs.appendFileSync(STATS_PATH, entry + "\n");
        } catch (e) {
            // Stats failure must not affect proxying
        }

        body_buffer = "";
        truncated = false;
    }

    r.sendBuffer(data, flags);
}

export default { accumulate };
