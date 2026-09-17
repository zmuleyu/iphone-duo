// Step 4.1D v2 bootstrap: shell motion blur first, scene second, unified world transition last.
// Loading the unified transition AFTER main.js guarantees the screen materials,
// uploaded texture targets and model meshes already exist before we wrap them.
await import('./motionblur381.js');
await import('./main.js');
await import('./worldtransition41d_v2.js');
