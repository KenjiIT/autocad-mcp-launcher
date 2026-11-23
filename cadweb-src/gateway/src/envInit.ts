// Import ĐẦU TIÊN trong index.ts: lọc env trước khi module khác đọc hay spawn gì.
import { cleanProcessEnv } from "./cleanEnv.js";
cleanProcessEnv();
