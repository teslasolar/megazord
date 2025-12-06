// UDT Schemas (ISA-88/95 Compliant)
const UDT = {
    GPU: {
        name: 'UDT_GPU',
        tag_prefix: 'GPUCluster_INF_GPU',
        fields: {
            h: { type: 'STRING[8]', desc: 'Hash ID (H() function)' },
            idx: { type: 'INT', desc: 'Device index 0..N-1' },
            name: { type: 'STRING[64]', desc: 'GPU product name' },
            state: { type: 'ENUM:ST', desc: 'PackML state' },
            temp: { type: 'INT', desc: 'Temperature °C', unit: '°C' },
            pwr: { type: 'INT', desc: 'Power draw', unit: 'W' },
            pwr_cap: { type: 'INT', desc: 'Power limit', unit: 'W' },
            vram_used: { type: 'INT', desc: 'VRAM used', unit: 'MB' },
            vram_total: { type: 'INT', desc: 'VRAM total', unit: 'MB' },
            util: { type: 'REAL', desc: 'Utilization 0-100', unit: '%' },
            models: { type: 'ARRAY[STRING]', desc: 'Loaded model hashes' }
        }
    },
    Model: {
        name: 'UDT_Model',
        tag_prefix: 'GPUCluster_MDL',
        fields: {
            h: { type: 'STRING[8]', desc: 'Hash ID (M() function)' },
            name: { type: 'STRING[64]', desc: 'Model name' },
            vram: { type: 'INT', desc: 'VRAM requirement', unit: 'MB' },
            shard: { type: 'BOOL', desc: 'Can shard across GPUs' },
            on_gpus: { type: 'ARRAY[STRING]', desc: 'GPU hashes where loaded' },
            req_cnt: { type: 'INT', desc: 'Total request count' }
        }
    },
    Request: {
        name: 'UDT_Request',
        tag_prefix: 'GPUCluster_INF_RTR_REQ',
        fields: {
            h: { type: 'STRING[8]', desc: 'Hash ID (R() function)' },
            model_h: { type: 'STRING[8]', desc: 'Target model hash' },
            state: { type: 'ENUM:RS', desc: 'Request state' },
            priority: { type: 'INT', desc: 'Queue priority 0-9' },
            queued_at: { type: 'DATETIME', desc: 'Queue timestamp' },
            tok_in: { type: 'INT', desc: 'Input tokens' },
            tok_out: { type: 'INT', desc: 'Output tokens' }
        }
    },
    Alarm: {
        name: 'UDT_Alarm',
        tag_prefix: 'GPUCluster_ALM',
        fields: {
            h: { type: 'STRING[8]', desc: 'Alarm hash' },
            tag: { type: 'STRING[64]', desc: 'Source tag' },
            class: { type: 'ENUM:AlarmClass', desc: 'CRIT/HIGH/MED/LOW' },
            message: { type: 'STRING[256]', desc: 'Alarm message' },
            t_raised: { type: 'DATETIME', desc: 'Time raised' },
            t_ack: { type: 'DATETIME', desc: 'Time acknowledged' },
            t_clear: { type: 'DATETIME', desc: 'Time cleared' },
            active: { type: 'BOOL', desc: 'Currently active' }
        }
    }
};

// State Enums
const ST = { OFF: 0, STARTING: 1, READY: 2, BUSY: 3, THROTTLE: 4, ERROR: 5 };
const ST_NAMES = ['OFF', 'STARTING', 'READY', 'BUSY', 'THROTTLE', 'ERROR'];
const RS = { QUEUED: 0, ROUTING: 1, LOADING: 2, PROCESSING: 3, COMPLETE: 4, ERROR: 5 };
const RS_NAMES = ['QUEUED', 'ROUTING', 'LOADING', 'PROCESSING', 'COMPLETE', 'ERROR'];
const AlarmClass = { CRIT: 1, HIGH: 2, MED: 3, LOW: 4 };

// Hash functions (8-char MD5 prefix simulation)
const H = (x) => 'H' + btoa(String(x)).slice(0, 7).replace(/[^a-zA-Z0-9]/g, 'x');
const M = (x) => 'M' + btoa(String(x)).slice(0, 7).replace(/[^a-zA-Z0-9]/g, 'x');
const R = (x) => 'R' + btoa(String(Date.now()) + String(x)).slice(0, 7).replace(/[^a-zA-Z0-9]/g, 'x');

// Tag generator
const makeTag = (prefix, idx, field) => `${prefix}${String(idx).padStart(2, '0')}_${field}`;
