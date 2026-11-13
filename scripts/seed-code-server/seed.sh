set -e
NODE=v22.23.5
cd "$HOME"
if [ ! -x "$HOME/.local/node-$NODE/bin/node" ]; then
  mkdir -p "$HOME/.local/node-$NODE"
  curl -fsSL https://nodejs.org/dist/$NODE/node-$NODE-linux-x64.tar.gz | tar -xz -C "$HOME/.local/node-$NODE" --strip-components=1
fi
sed -i '/local\/node/d' "$HOME/.bashrc"
echo "export PATH=\"\$HOME/.local/node-$NODE/bin:\$PATH\"" >> "$HOME/.bashrc"
mkdir -p "$HOME/project"
cd "$HOME/project"
tar -xf /tmp/todo-api.tar
cd todo-api
if [ ! -d .git ]; then
  git init -q -b main && git add -A && git -c user.name=Demo -c user.email=demo@example.com commit -qm "Initial todo-api"
fi
"$HOME/.local/node-$NODE/bin/node" --version
echo SEED-DONE
grep -q 'PS1=.*coder' "$HOME/.bashrc" || echo 'PS1='"'"'\[\e[32m\]coder\[\e[0m\]:\[\e[34m\]\w\[\e[0m\]\$ '"'" >> "$HOME/.bashrc"
"$HOME/.local/node-$NODE/bin/node" "$HOME/.local/node-$NODE/bin/npm" config set update-notifier false
