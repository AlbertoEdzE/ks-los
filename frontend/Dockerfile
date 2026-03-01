FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* /app/
RUN if [ -f package.json ]; then npm ci || true; fi
COPY . /app
RUN if [ -f package.json ]; then npm run build || npm run build; fi

FROM nginx:alpine AS serve
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
