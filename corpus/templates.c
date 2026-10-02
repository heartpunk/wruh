typedef unsigned long u64;
typedef unsigned int u32;
typedef unsigned char u8;
__attribute__((noinline)) u64 arithmetic(u64 a,u64 b){return ((a+b)*(a-b)) ^ (a&b) ^ (a|b) ^ ~a;}
u64 shifts(u64 a,u64 b){return (a << (b&63)) ^ (a >> (b&63));}
long signed_shift(long a,u64 b){return a >> (b&63);}
u64 division(u64 a,u64 b){return b ? a/b + a%b : 0;}
u64 branch(u64 a,u64 b){if(a<b)return a+3;else return b-7;}
long signed_branch(long a,long b){return a<=b ? a : b;}
u64 loop(u64 *p,u64 n){u64 s=0;for(u64 i=0;i<n;i++)s+=p[i];return s;}
u32 alias(u32 *a,u32 *b,u32 x){*a=x;return *b;}
u32 overlap(u8 *p,u32 x){p[0]=x;p[1]=x>>8;return p[0]|((u32)p[1]<<8);}
u64 widths(u8 *a,u32 *b,u64 *c){*a+=1;*b+=2;*c+=3;return *a+*b+*c;}
long extend(signed char a, unsigned short b){return a+(long)b;}
u64 call(u64 a,u64 b){return arithmetic(a,b)+1;}
