import os
import sys
import modules.paths_internal


data_path = modules.paths_internal.data_path
script_path = modules.paths_internal.script_path
models_path = modules.paths_internal.models_path
sd_configs_path = modules.paths_internal.sd_configs_path
sd_default_config = modules.paths_internal.sd_default_config
sd_model_file = modules.paths_internal.sd_model_file
default_sd_model_file = modules.paths_internal.default_sd_model_file
extensions_dir = modules.paths_internal.extensions_dir
extensions_builtin_dir = modules.paths_internal.extensions_builtin_dir

def mute_sdxl_imports():
    """create fake modules that SDXL wants to import but doesn't actually use for our purposes"""

    class Dummy:
        pass

    module = Dummy()
    module.LPIPS = None
    sys.modules['taming.modules.losses.lpips'] = module

    module = Dummy()
    module.StableDataModuleFromConfig = None
    sys.modules['sgm.data'] = module

# data_path = cmd_opts_pre.data
sys.path.insert(0, script_path)

# search for directory of stable diffusion in following places
sd_path = None
possible_sd_paths = [os.path.join(script_path, 'repositories/stable-diffusion-stability-ai'), '.', os.path.dirname(script_path)]
for possible_sd_path in possible_sd_paths:
    if os.path.exists(os.path.join(possible_sd_path, 'ldm/models/diffusion/ddpm.py')):
        sd_path = os.path.abspath(possible_sd_path)
        break

assert sd_path is not None, f"Couldn't find Stable Diffusion in any of: {possible_sd_paths}"

mute_sdxl_imports()

path_dirs = [
    (sd_path, 'ldm', 'Stable Diffusion', []),
    (os.path.join(sd_path, '../generative-models'), 'sgm', 'Stable Diffusion XL', ["sgm"]),
    (os.path.join(sd_path, '../taming-transformers'), 'taming', 'Taming Transformers', []),
    (os.path.join(sd_path, '../CodeFormer'), 'inference_codeformer.py', 'CodeFormer', []),
    (os.path.join(sd_path, '../BLIP'), 'models/blip.py', 'BLIP', []),
    (os.path.join(sd_path, '../k-diffusion'), 'k_diffusion/sampling.py', 'k_diffusion', ["atstart"]),
]

paths = {}

for d, must_exist, what, _options in path_dirs:
    must_exist_path = os.path.abspath(os.path.join(script_path, d, must_exist))
    if not os.path.exists(must_exist_path):
        print(f"Warning: {what} not found at path {must_exist_path}", file=sys.stderr)
    else:
        d = os.path.abspath(d)
        if "atstart" in _options:
            sys.path.insert(0, d)
        elif "sgm" in _options:
            # Stable Diffusion XL repo has scripts dir with __init__.py in it which ruins every extension's scripts dir, so we
            # import sgm and remove it from sys.path so that when a script imports scripts.something, it doesbn't use sgm's scripts dir.

            sys.path.insert(0, d)
            import sgm

            sys.path.pop(0)
        else:
            sys.path.append(d)
        paths[what] = d


def create_paths(opts, log=None):
    def create_path(folder):
        if folder is None or folder == '':
            return
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
                if log is not None:
                    log.debug(f'Create path: {folder}')
            except Exception as e:
                if log is not None:
                    log.error(f'Failed to create path: {folder} {e}')

    def fix_path(folder):
        tgt = opts.data.get(folder, None) or opts.data_labels[folder].default
        if tgt is None or tgt == '':
            return tgt
        if len(data_path) > 0 and tgt.startswith(data_path): # path is already relative to data_path
            return tgt
        fullpath = os.path.join(data_path, tgt)
        if len(data_path) > 0 and os.path.isabs(data_path):
            return fullpath
        if os.path.isabs(fullpath) and os.path.exists(fullpath):
            return fullpath
        try:
            relpath = os.path.relpath(fullpath, script_path)
            opts.data[folder] = relpath
        except Exception:
            opts.data[folder] = fullpath
        return opts.data[folder]

    create_path(data_path)
    create_path(script_path)
    create_path(models_path)
    create_path(sd_configs_path)
    create_path(extensions_dir)
    create_path(extensions_builtin_dir)
    create_path(fix_path('temp_dir'))
    create_path(fix_path('hypernetwork_dir'))
    create_path(fix_path('ckpt_dir'))
    create_path(fix_path('vae_dir'))
    create_path(fix_path('diffusers_dir'))
    create_path(fix_path('embeddings_dir'))
    create_path(fix_path('outdir_samples'))
    create_path(fix_path('outdir_txt2img_samples'))
    create_path(fix_path('outdir_img2img_samples'))
    create_path(fix_path('outdir_extras_samples'))
    create_path(fix_path('outdir_grids'))
    create_path(fix_path('outdir_txt2img_grids'))
    create_path(fix_path('outdir_img2img_grids'))
    create_path(fix_path('outdir_save'))
    create_path(fix_path('styles_dir'))


class Prioritize:
    def __init__(self, name):
        self.name = name
        self.path = None

    def __enter__(self):
        self.path = sys.path.copy()
        sys.path = [paths[self.name]] + sys.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.path = self.path
        self.path = None
