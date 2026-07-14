# GitHub 提交命令参考

如果把本文件夹作为一个新的 GitHub 仓库提交，可以在 `kangnong_week4_github_submission` 目录下执行：

```bash
git init
git add .
git commit -m "Add Kangnong prospectus reproducible case study"
git branch -M main
git remote add origin <你的GitHub仓库地址>
git push -u origin main
```

如果是提交到已有仓库，建议把整个 `kangnong_week4_github_submission` 文件夹复制到仓库中，然后执行：

```bash
git add kangnong_week4_github_submission
git commit -m "Add Kangnong Week4 reproducible homework"
git push
```

提交前请先运行：

```bash
python run_pipeline.py
python code/check_submission.py
```

看到 `SUBMISSION CHECK PASSED` 后再提交。
