// CRA/Jest 27 needs these web primitives before react-router v7 is imported.
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder ||= TextEncoder;
global.TextDecoder ||= TextDecoder;
