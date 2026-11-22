// actions/deploy-pages#413: its bundled artifact client still imports core punycode.
// Use the unchanged userland implementation in this Node process only. Warnings
// remain enabled; remove this adapter once the official action fixes its bundle.
import {registerHooks} from 'node:module';

const replacement = new URL('./vendor/punycode.cjs', import.meta.url).href;
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === 'punycode' || specifier === 'node:punycode') {
      return {url: replacement, format: 'commonjs', shortCircuit: true};
    }
    return nextResolve(specifier, context);
  }
});
