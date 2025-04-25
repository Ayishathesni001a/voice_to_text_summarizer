{pkgs}: {
  deps = [
    pkgs.ffmpeg-full
    pkgs.portaudio
    pkgs.glibcLocales
    pkgs.freetype
    pkgs.postgresql
    pkgs.openssl
  ];
}
