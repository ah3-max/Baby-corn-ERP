FROM node:20-alpine

WORKDIR /app

# 複製專案程式碼（node_modules 由 volume 掛載）
COPY . .

# 開發模式啟動（支援熱重載）
CMD ["npm", "run", "dev"]
