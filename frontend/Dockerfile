FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend .

# VITE_* values are baked in at build time (the browser calls the backend directly)
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_API_KEY=changeme
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_KEY=$VITE_API_KEY

RUN npm run build

EXPOSE 5174

CMD ["npm", "run", "preview", "--", "--host", "--port", "5174"]
