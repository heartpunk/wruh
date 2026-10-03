extern unsigned long child(unsigned long);
unsigned long direct_root(unsigned long x) { return child(x) + 1; }
unsigned long indirect_root(unsigned long (*function)(unsigned long), unsigned long x) { return function(x) + 1; }
unsigned long tail_root(unsigned long x) { return child(x); }
