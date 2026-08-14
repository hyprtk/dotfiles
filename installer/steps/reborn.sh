#!/bin/bash
# reborn distro steps — os-release to /usr/lib/ (no splash/bootctl),
# multiline sudoers, backs up existing hypr config.

pre_hypr_symlink() {
    [ -e ~/.config/hypr ] && mv ~/.config/hypr ~/.config/hypr-old
}

setup_sudoers() {
    echo -e '
        Defaults env_reset,pwfeedback'| sudo tee -a /etc/sudoers
}
