#!/bin/bash  

programs=("azd" "git" "python" "npm" "tsc" "vite")

for program in "${programs[@]}"; do
    if which "$program" > /dev/null; then
        echo "$program is installed!"
    else
        echo "$program is not installed!"
        exit 1
    fi
done

echo ""  
echo "Loading azd .env file from current environment"  
echo ""  
  
while IFS='=' read -r key value; do  
  export "$key=$value"  
done < <(azd env get-values)  
  
if [ $? -ne 0 ]; then  
  echo "Failed to load environment variables from azd environment"  
  exit 1  
fi  
  
echo ""  
echo "Restoring backend python packages"  
echo ""  
cd backend  
pip install -r requirements.txt  
  
if [ $? -ne 0 ]; then  
  echo "Failed to restore backend python packages"  
  exit 1  
fi  
  
echo ""  
echo "Restoring frontend npm packages"  
echo ""  
cd ../frontend  
npm install  
  
if [ $? -ne 0 ]; then  
  echo "Failed to restore frontend npm packages"  
  exit 1  
fi  
  
echo ""  
echo "Building frontend"  
echo ""  
npm run build  
  
if [ $? -ne 0 ]; then  
  echo "Failed to build frontend"  
  exit 1  
fi  
  
echo ""  
echo "Starting backend"  
echo ""  
cd ../backend  
python ./app.py &  
  
if [ $? -ne 0 ]; then  
  echo "Failed to start backend"  
  exit 1  
fi  
  
exit 0  
