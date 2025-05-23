   #!/bin/bash

   for d in backend/*/ frontend/app/src; do
     name=$(basename "$d" | sed 's/^app$/frontend_src/')
     (cd "$d" && snap2txt && mv -f project_contents.txt "${name}_contents.txt")
   done