/** Publish notices from an independent Node process for the cross-runtime gate. */
import {FileInvalidationBus} from "./engine.ts";

const bus = new FileInvalidationBus(process.argv[2]);
for (let index = 0; index < 40; index++) bus.publish(`/node/${index}`);
bus.close();
