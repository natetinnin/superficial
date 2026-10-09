#!/usr/bin/env bash
# Generate placeholder clips + a 96 bpm drum loop so the pipeline can be tried
# without any real footage:  bash scripts/make_demo_assets.sh demo
set -euo pipefail
out=${1:-demo}
mkdir -p "$out/clips" "$out/outro"
gen() { ffmpeg -y -v error -f lavfi -i "$1" -t 6 -pix_fmt yuv420p "$out/clips/$2.mp4"; }
gen "testsrc2=s=1280x720:r=24" a_testsrc
gen "mandelbrot=s=1280x720:r=24" b_mandelbrot
gen "life=s=640x360:r=24:mold=10:ratio=0.1:death_color=#202020:life_color=#e0e0e0,scale=1280:720:flags=neighbor" c_life
gen "cellauto=s=1280x720:r=24:rule=110" d_cellauto
gen "gradients=s=1280x720:r=24:speed=0.03" e_gradients
gen "smptehdbars=s=1280x720:r=24,hue=H=2*PI*t/6" f_bars
gen "rgbtestsrc=s=1280x720:r=24,rotate=0.3*t" g_rotate
gen "color=c=#303030:s=1280x720:r=24,drawtext=text='%{pts\\:hms}':fontsize=120:fontcolor=white:x=(w-tw)/2:y=(h-th)/2" h_clock
for label in PRADA GOTHIC; do
  ffmpeg -y -v error -f lavfi -i "color=c=black:s=1280x720" -frames:v 1 \
    -vf "drawbox=x=380:y=300:w=520:h=120:c=#e8e6e0:t=fill,drawtext=text='$label':fontsize=64:fontcolor=#222222:x=(w-tw)/2:y=(h-th)/2" \
    "$out/outro/$label.png"
done
# 96 bpm: kick on every beat, snare on 2 & 4, hats on 8ths, a bass drone
ffmpeg -y -v error -f lavfi -i "aevalsrc=\
'0.9*sin(2*PI*55*t)*exp(-18*mod(t,0.625))\
+0.5*(random(0)-0.5)*exp(-25*mod(t-0.625,1.25))*gte(t,0.625)\
+0.15*(random(1)-0.5)*exp(-60*mod(t,0.3125))\
+0.15*sin(2*PI*41.2*t)':s=44100:d=40" -ac 2 "$out/track.wav"
echo "demo assets in $out/"
