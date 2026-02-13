// stats.js — Response body accumulation + POST to LMGate /stats
// Uses js_body_filter to accumulate response body chunks.
// On last chunk, fires ngx.fetch() POST to LMGate /stats.

var body_buffer = "";
var MAX_BODY_SIZE = 2 * 1024 * 1024; // 2 MB cap
var truncated = false;

function accumulate(r, data, flags) {
    if (!truncated && body_buffer.length + data.length <= MAX_BODY_SIZE) {
        body_buffer += data;
    } else {
        truncated = true;
    }

    if (flags.last) {
        var payload = JSON.stringify({
            timestamp: new Date().toISOString(),
            client_ip: r.remoteAddress,
            method: r.variables.request_method,
            uri: r.variables.request_uri,
            host: r.headersOut["X-Upstream-Host"] || "",
            status: r.status,
            auth_key_header: r.headersIn["Authorization"] || "",
            auth_x_api_key: r.headersIn["X-Api-Key"] || "",
            lmgate_internal_id: r.variables.lmgate_id || "",
            response_body: truncated ? "" : body_buffer,
            body_truncated: truncated
        });

        ngx.fetch("http://lmgate:8081/stats", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: payload
        }).catch(function(e) {
            // Fire-and-forget: stats failure must not affect proxying
        });

        body_buffer = "";
        truncated = false;
    }

    r.sendBuffer(data, flags);
}

export default { accumulate };
